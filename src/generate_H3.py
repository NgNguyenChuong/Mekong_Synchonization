import os
import h3
import geopandas as gpd

from shapely.geometry import Polygon
from shapely.ops import unary_union

from config import (
    H3_RES,
    CRS_WGS84,
    CRS_METRIC,
    BUFFER_DIST,
    PATH_SHP_BOUNDARY,
    DATA_OUT
)

# ============================================================
# H3 COMPATIBILITY (v3 / v4)
# ============================================================
def get_h3_funcs():
    v = int(h3.__version__.split('.')[0])
    if v >= 4:
        return h3.latlng_to_cell, h3.cell_to_boundary
    else:
        return h3.geo_to_h3, h3.h3_to_geo_boundary


to_cell_func, to_boundary_func = get_h3_funcs()

# ============================================================
# LOAD ROI (ĐBSCL boundary)
# ============================================================
print("🔍 Đọc ranh giới ĐBSCL...")
roi_gdf = gpd.read_file(PATH_SHP_BOUNDARY).to_crs(CRS_WGS84)
print("✅ Boundary loaded")

# ============================================================
# H3 GRID GENERATION
# ============================================================
def generate_h3_grid(gdf, resolution):

    # Buffer để bắt đủ mép biển
    print(f"--> Buffer {BUFFER_DIST:.0f} m")
    gdf_metric = gdf.to_crs(CRS_METRIC)
    gdf_buffered = gdf_metric.buffer(BUFFER_DIST).to_crs(CRS_WGS84)

    hex_set = set()

    for geom in gdf_buffered.geometry:
        geoms = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]

        for g in geoms:
            if hasattr(h3, "polygon_to_cells"):
                from h3 import LatLngPoly
                outer = [(lat, lon) for lon, lat in g.exterior.coords]
                h3_poly = LatLngPoly(outer)
                hex_set.update(h3.polygon_to_cells(h3_poly, resolution))
            else:
                from shapely.geometry import mapping
                hex_set.update(h3.polyfill(mapping(g), resolution))

    print(f"--> Polyfill: {len(hex_set)} cell")

    # Cắt lại theo boundary thật
    union_poly = unary_union(gdf.geometry)
    valid_hex = []
    hex_geom = []

    for h in hex_set:
        boundary = to_boundary_func(h)
        coords = [(lon, lat) for lat, lon in boundary]
        poly = Polygon(coords)

        if poly.intersects(union_poly):
            valid_hex.append(h)
            hex_geom.append(poly)

    return gpd.GeoDataFrame(
        {"h3_index": valid_hex},
        geometry=hex_geom,
        crs=CRS_WGS84
    )

# ============================================================
# RUN
# ============================================================
print("⚙️ Sinh lưới H3...")
h3_grid = generate_h3_grid(roi_gdf, H3_RES)

print(f"📊 Tổng số ô H3: {len(h3_grid)}")

# Save output
out_path = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")
h3_grid.to_file(out_path, driver="GeoJSON")

print(f"💾 Lưu tại: {out_path}")
print("✅ Hoàn tất sinh lưới H3.")