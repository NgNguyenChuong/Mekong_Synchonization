import os
import geopandas as gpd
import h3
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from shapely.ops import unary_union
from config import (
    DATA_RAW, SHAPEFILE_RAW, SHAPEFILE_CLEAN,
    CRS_METRIC, CRS_WGS84, MIN_ISLAND_AREA_KM2,
    H3_GRID_GEOJSON, H3_RESOLUTION, BUFFER_DIST
)

# -----------------------------------------------------------
# 1. INPUT SHAPEFILE RESOLUTION
# -----------------------------------------------------------
# def _find_shapefiles_in_raw():
#     if not os.path.exists(DATA_RAW):
#         return []
#     return sorted(
#         os.path.join(DATA_RAW, f)
#         for f in os.listdir(DATA_RAW)
#         if f.lower().endswith(".shp")
#     )


# def _resolve_input_shapefile():
#     candidates = _find_shapefiles_in_raw()
#     if len(candidates) == 1:
#         selected = candidates[0]
#         print(f"    Using input shapefile: {selected}")
#         return selected
#     if len(candidates) > 1:
#         names = "\n      - " + "\n      - ".join(candidates)
#         raise ValueError(
#             "Multiple shapefiles found in data/raw. "
#             "Keep exactly one .shp before running pipeline:" + names
#         )

#     # bỏ fallback 
#     # if ENABLE_GEE_FALLBACK:
#     #     return download_shapefile_gee()

#     raise FileNotFoundError(
#         "No input shapefile found. Add exactly one .shp to data/raw. "
#     )


# # -----------------------------------------------------------
# # 2. DOWNLOAD SHAPEFILE FROM GEE (OPTIONAL FALLBACK)
# # -----------------------------------------------------------
# def download_shapefile_gee():
#     print("   🌍 Authenticating & Initializing GEE...")
#     if GEE_PROJECT:
#         try:
#             ee.Initialize(project=GEE_PROJECT)
#         except Exception:
#             print("   ⚠️  GEE Init with project failed. Trying generic ee.Initialize()...")
#             ee.Initialize()
#     else:
#         ee.Initialize()

#     print("   ⬇️  Downloading boundary from GEE...")
#     if not GEE_TARGET_AREAS:
#         raise ValueError("GEE fallback requires at least one name in GEE_TARGET_AREAS.")

#     admin_fc = ee.FeatureCollection(GEE_ADMIN_COLLECTION)
#     target_fc = admin_fc.filter(ee.Filter.inList(GEE_ADMIN_NAME_FIELD, GEE_TARGET_AREAS))

#     geemap.ee_export_vector(target_fc, filename=SHAPEFILE_RAW)
#     print(f"   ✅ Downloaded boundary to: {SHAPEFILE_RAW}")
#     return SHAPEFILE_RAW


# -----------------------------------------------------------
# 3. CLEAN SHAPEFILE (REMOVE SMALL ISLANDS)
# -----------------------------------------------------------
def clean_shapefile():
    if os.path.exists(SHAPEFILE_CLEAN) and os.path.getmtime(SHAPEFILE_CLEAN) >= os.path.getmtime(SHAPEFILE_RAW):
        print(f"    Cleaned shapefile already exists: {SHAPEFILE_CLEAN}")
        return SHAPEFILE_CLEAN

    print("    Cleaning shapefile (removing small islands as option)...")
    if not os.path.exists(SHAPEFILE_RAW):
        raise FileNotFoundError(f" Input shapefile missing: {SHAPEFILE_RAW}")

    gdf = gpd.read_file(SHAPEFILE_RAW)
    gdf_metric = gdf.to_crs(CRS_METRIC)

    gdf_exploded = gdf_metric.explode(index_parts=True).reset_index(drop=True)
    gdf_exploded['area_km2'] = gdf_exploded.geometry.area / 1e6

    if MIN_ISLAND_AREA_KM2 > 0:
        gdf_clean = gdf_exploded[gdf_exploded['area_km2'] > MIN_ISLAND_AREA_KM2].copy()
    else:
        gdf_clean = gdf_exploded.copy()

    gdf_final = gdf_clean.dissolve().to_crs(CRS_WGS84)
    
    gdf_final.to_file(SHAPEFILE_CLEAN)
    print(f"    Cleaned shapefile saved: {SHAPEFILE_CLEAN}")
    return SHAPEFILE_CLEAN


# -----------------------------------------------------------
# 4. GENERATE H3 GRID (Fixed API: h3.LatLngPoly)
# -----------------------------------------------------------
def generate_h3_grid():
    if os.path.exists(H3_GRID_GEOJSON) and os.path.getmtime(H3_GRID_GEOJSON) >= os.path.getmtime(SHAPEFILE_CLEAN):
        print(f"    H3 Grid already exists: {H3_GRID_GEOJSON}")
        return

    print("   HEX Generating H3 Grid (v4)...")

    if not os.path.exists(SHAPEFILE_CLEAN):
        raise FileNotFoundError(f" Cleaned shapefile missing: {SHAPEFILE_CLEAN}")

    gdf = gpd.read_file(SHAPEFILE_CLEAN).to_crs(CRS_WGS84)
    
    # Tạo buffer để bao phủ rìa biển
    if BUFFER_DIST > 0:
        gdf_metric = gdf.to_crs(CRS_METRIC)
        buffered_geoms = gdf_metric.buffer(BUFFER_DIST).to_crs(CRS_WGS84)
    else:
        buffered_geoms = gdf.geometry

    hex_set = set()

    # Loop qua từng geometry
    for geom in buffered_geoms:
        geoms = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        
        for g in geoms:
            # --- [CORRECT H3 v4 LOGIC] ---
            
            # 1. Outer Ring: (Lon, Lat) -> (Lat, Lon)
            outer = [(lat, lon) for lon, lat in g.exterior.coords]
            
            # 2. Holes: (Lon, Lat) -> (Lat, Lon)
            holes = []
            for interior in g.interiors:
                holes.append([(lat, lon) for lon, lat in interior.coords])
            
            # 3. Sử dụng h3.LatLngPoly (API chuẩn)
            try:
                poly = h3.LatLngPoly(outer, holes) # Không dùng *holes
                
                # 4. Fill Cells
                cells = h3.polygon_to_cells(poly, H3_RESOLUTION)
                hex_set.update(cells)
            except Exception as e:
                print(f"⚠️ Error polyfilling: {e}")
                continue

    print(f"   --> Generated {len(hex_set)} candidate cells.")

    # --- CLIPPING (OPTIMIZED với STRtree) ---
    print("     Clipping to exact boundary...")
    union_poly = unary_union(gdf.geometry)

    # OPTIMIZED: Tạo tất cả hex polygons trước
    hex_list = list(hex_set)
    hex_geoms_all = []
    for h in hex_list:
        # H3 v4: cell_to_boundary trả về tuple ((lat, lon), ...)
        boundary = h3.cell_to_boundary(h)
        # Đảo ngược (Lat, Lon) -> (Lon, Lat) cho Shapely Polygon
        poly_coords = [(p[1], p[0]) for p in boundary]
        hex_geoms_all.append(Polygon(poly_coords))

    # OPTIMIZED: Sử dụng STRtree để query nhanh
    tree = STRtree(hex_geoms_all)

    # Query tất cả hex intersects với boundary
    valid_indices = tree.query(union_poly, predicate='intersects')

    valid_hex = [hex_list[i] for i in valid_indices]
    hex_geoms = [hex_geoms_all[i] for i in valid_indices]

    # Save
    gdf_hex = gpd.GeoDataFrame(
        {"h3_index": valid_hex},
        geometry=hex_geoms,
        crs=CRS_WGS84
    )
    
    gdf_hex.to_file(H3_GRID_GEOJSON, driver="GeoJSON")
    print(f"    H3 Grid saved: {H3_GRID_GEOJSON} ({len(gdf_hex)} cells)")


# -----------------------------------------------------------
# MAIN WRAPPER
# -----------------------------------------------------------
def run_preprocessing():
    print("--- [PREPROCESSING] ---")
    clean_shapefile()
    generate_h3_grid()
    print("-----------------------")
