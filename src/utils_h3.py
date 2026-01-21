# utils_h3.py
import os
import re
import rasterio
import geopandas as gpd
import random
from shapely.geometry import Point

def parse_year_month(fname):
    """Parse năm-tháng từ tên file"""
    m = re.search(r"(\d{4})_(\d{1,2})", fname)
    if not m:
        raise ValueError(f"Không đọc được năm-tháng từ {fname}")
    return int(m.group(1)), int(m.group(2))


def index_files(folder):
    """Index tất cả .tif files theo (year, month)"""
    return {
        parse_year_month(f): os.path.join(folder, f)
        for f in os.listdir(folder) if f.endswith(".tif")
    }


def load_h3_centroids(h3_path, crs_metric, crs_wgs84):
    """
    Load H3 grid và trả về centroids
    (Legacy function - dùng cho code đơn giản)
    """
    h3 = gpd.read_file(h3_path)
    h3_metric = h3.to_crs(crs_metric)
    h3["centroid"] = h3_metric.centroid.to_crs(crs_wgs84)
    points = [(p.x, p.y) for p in h3.centroid]
    return h3["h3_index"].tolist(), points


def get_h3_sample_points(hex_geom):
    """
    Tạo 7 điểm sample cho 1 ô H3:
    - 1 centroid
    - 6 midpoint của mỗi cạnh
    """
    pts = []
    
    # Centroid
    c = hex_geom.centroid
    pts.append((c.x, c.y))
    
    # Midpoint của 6 cạnh
    coords = list(hex_geom.exterior.coords)
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        pts.append(((x1 + x2) / 2, (y1 + y2) / 2))
    
    return pts


def load_h3_multipoints(h3_path, crs_metric, crs_wgs84):
    """
    Load H3 grid và trả về 7 điểm sample cho mỗi cell
    
    Returns:
        h3_ids: list of h3_index
        point_groups: list of [(x,y), ...] - 7 điểm cho mỗi cell
    """
    h3 = gpd.read_file(h3_path)
    h3_metric = h3.to_crs(crs_metric)
    h3_wgs = h3_metric.to_crs(crs_wgs84)
    
    h3_ids = h3["h3_index"].tolist()
    point_groups = [get_h3_sample_points(geom) for geom in h3_wgs.geometry]
    
    return h3_ids, point_groups, list(h3_wgs.geometry)


def sample_multiband(tif_path, points):
    """
    Sample đơn giản - chỉ lấy giá trị tại 1 điểm/cell
    (Legacy function - giữ để backward compatible)
    """
    with rasterio.open(tif_path) as src:
        data = list(src.sample(points))
        nodata = src.nodata
    return data, nodata


def is_nodata(value, nodata):
    """
    Kiểm tra xem value có phải nodata không
    Xử lý cả int, float và floating point precision
    """
    if value is None or nodata is None:
        return value is None
    
    # So sánh với tolerance cho floating point
    import math
    try:
        return math.isclose(float(value), float(nodata), rel_tol=1e-9, abs_tol=1e-9)
    except (ValueError, TypeError):
        return value == nodata
def random_points_in_polygon(poly, n):
    """
    Sinh n điểm ngẫu nhiên nằm trong polygon
    """
    minx, miny, maxx, maxy = poly.bounds
    points = []

    while len(points) < n:
        p = Point(
            random.uniform(minx, maxx),
            random.uniform(miny, maxy)
        )
        if poly.contains(p):
            points.append((p.x, p.y))
    return points

def sample_multiband_robust(
    tif_path,
    point_groups,
    h3_geoms=None,
    n_random=10
):
    with rasterio.open(tif_path) as src:
        nodata = src.nodata
        num_bands = src.count
        num_cells = len(point_groups)

        vals = [[None] * num_bands for _ in range(num_cells)]

        for band_idx in range(num_bands):
            for i, points in enumerate(point_groups):

                # -------- Strategy 1: centroid --------
                try:
                    v = next(src.sample([points[0]], indexes=band_idx + 1))[0]
                    if not is_nodata(v, nodata):
                        vals[i][band_idx] = float(v)
                        continue
                except:
                    pass

                # -------- Strategy 2: 6 midpoint --------
                valid_vals = []
                for pt in points[1:]:
                    try:
                        v = next(src.sample([pt], indexes=band_idx + 1))[0]
                        if not is_nodata(v, nodata):
                            valid_vals.append(v)
                    except:
                        pass

                if valid_vals:
                    vals[i][band_idx] = float(sum(valid_vals) / len(valid_vals))
                    continue

                # -------- Strategy 3: random in H3 --------
                if h3_geoms is not None:
                    rand_pts = random_points_in_polygon(h3_geoms[i], n_random)
                    rand_vals = []
                    for pt in rand_pts:
                        try:
                            v = next(src.sample([pt], indexes=band_idx + 1))[0]
                            if not is_nodata(v, nodata):
                                rand_vals.append(v)
                        except:
                            pass

                    if rand_vals:
                        vals[i][band_idx] = float(sum(rand_vals) / len(rand_vals))

        return vals, nodata



# Test ở cuối file utils_h3.py
if __name__ == "__main__":
    # Test nodata detection
    assert is_nodata(-9999.0, -9999) == True
    assert is_nodata(-9999, -9999.0) == True
    assert is_nodata(-9998.99999, -9999.0) == True  # floating point tolerance
    assert is_nodata(0.0, -9999) == False
    assert is_nodata(None, -9999) == True
    print("✅ All nodata tests passed")