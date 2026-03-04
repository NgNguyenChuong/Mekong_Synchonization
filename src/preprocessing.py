import os
import ee
import geemap
import geopandas as gpd
import h3
from shapely.geometry import Polygon
from shapely.ops import unary_union
from config import (
    GEE_PROJECT, MEKONG_PROVINCES, SHAPEFILE_RAW, SHAPEFILE_CLEAN,
    CRS_METRIC, CRS_WGS84, MIN_ISLAND_AREA_KM2,
    H3_GRID_GEOJSON, H3_RESOLUTION, BUFFER_DIST
)

# -----------------------------------------------------------
# 1. DOWNLOAD SHAPEFILE FROM GEE
# -----------------------------------------------------------
def download_shapefile_gee():
    if os.path.exists(SHAPEFILE_RAW):
        print(f"   ✅ Raw shapefile already exists: {SHAPEFILE_RAW}")
        return

    print("   🌍 Authenticating & Initializing GEE...")
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        print("   ⚠️  GEE Init failed. Trying generic ee.Initialize()...")
        ee.Initialize()

    print("   ⬇️  Downloading Mekong Delta boundary...")
    vietnam = ee.FeatureCollection("FAO/GAUL/2015/level1")
    dbscl_fc = vietnam.filter(ee.Filter.inList('ADM1_NAME', MEKONG_PROVINCES))

    geemap.ee_export_vector(dbscl_fc, filename=SHAPEFILE_RAW)
    print(f"   ✅ Downloaded to: {SHAPEFILE_RAW}")


# -----------------------------------------------------------
# 2. CLEAN SHAPEFILE (REMOVE SMALL ISLANDS)
# -----------------------------------------------------------
def clean_shapefile():
    if os.path.exists(SHAPEFILE_CLEAN):
        print(f"   ✅ Cleaned shapefile already exists: {SHAPEFILE_CLEAN}")
        return

    print("   🧹 Cleaning shapefile (removing small islands)...")
    
    if not os.path.exists(SHAPEFILE_RAW):
        raise FileNotFoundError(f"❌ Raw shapefile missing: {SHAPEFILE_RAW}")

    gdf = gpd.read_file(SHAPEFILE_RAW)
    gdf_metric = gdf.to_crs(CRS_METRIC)
    
    gdf_exploded = gdf_metric.explode(index_parts=True).reset_index(drop=True)
    gdf_exploded['area_km2'] = gdf_exploded.geometry.area / 1e6
    
    gdf_clean = gdf_exploded[gdf_exploded['area_km2'] > MIN_ISLAND_AREA_KM2].copy()
    gdf_final = gdf_clean.dissolve().to_crs(CRS_WGS84)
    
    gdf_final.to_file(SHAPEFILE_CLEAN)
    print(f"   ✅ Cleaned shapefile saved: {SHAPEFILE_CLEAN}")


# -----------------------------------------------------------
# 3. GENERATE H3 GRID (Fixed API: h3.LatLngPoly)
# -----------------------------------------------------------
def generate_h3_grid():
    if os.path.exists(H3_GRID_GEOJSON):
        print(f"   ✅ H3 Grid already exists: {H3_GRID_GEOJSON}")
        return

    print("   HEX Generating H3 Grid (v4)...")
    
    if not os.path.exists(SHAPEFILE_CLEAN):
        raise FileNotFoundError(f"❌ Cleaned shapefile missing: {SHAPEFILE_CLEAN}")

    gdf = gpd.read_file(SHAPEFILE_CLEAN).to_crs(CRS_WGS84)
    
    # Tạo buffer để bao phủ rìa biển
    gdf_metric = gdf.to_crs(CRS_METRIC)
    gdf_buffered = gdf_metric.buffer(BUFFER_DIST).to_crs(CRS_WGS84)

    hex_set = set()

    # Loop qua từng geometry
    for geom in gdf_buffered.geometry:
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

    # --- CLIPPING ---
    print("   ✂️  Clipping to exact boundary...")
    union_poly = unary_union(gdf.geometry)
    
    valid_hex = []
    hex_geoms = []

    for h in hex_set:
        # H3 v4: cell_to_boundary trả về tuple ((lat, lon), ...)
        boundary = h3.cell_to_boundary(h)
        
        # Đảo ngược (Lat, Lon) -> (Lon, Lat) cho Shapely Polygon
        poly_coords = [(p[1], p[0]) for p in boundary]
        poly = Polygon(poly_coords)
        
        if poly.intersects(union_poly):
            valid_hex.append(h)
            hex_geoms.append(poly)

    # Save
    gdf_hex = gpd.GeoDataFrame(
        {"h3_index": valid_hex},
        geometry=hex_geoms,
        crs=CRS_WGS84
    )
    
    gdf_hex.to_file(H3_GRID_GEOJSON, driver="GeoJSON")
    print(f"   💾 H3 Grid saved: {H3_GRID_GEOJSON} ({len(gdf_hex)} cells)")


# -----------------------------------------------------------
# MAIN WRAPPER
# -----------------------------------------------------------
def run_preprocessing():
    print("--- [PREPROCESSING] ---")
    download_shapefile_gee()
    clean_shapefile()
    generate_h3_grid()
    print("-----------------------")