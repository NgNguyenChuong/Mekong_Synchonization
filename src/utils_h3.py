import os
import re
import random
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import math

# -----------------------------------------------------------
# File Helpers
# -----------------------------------------------------------
def parse_year_month(fname):
    """Parse năm-tháng từ tên file"""
    m = re.search(r"(\d{4})_(\d{1,2})", fname)
    if not m:
        # Thử format khác nếu cần, hoặc log warning
        return None
    return int(m.group(1)), int(m.group(2))

def index_files(folder):
    """Index tất cả .tif files theo (year, month)"""
    if not os.path.exists(folder):
        print(f"⚠️ Warning: Folder not found: {folder}")
        return {}
        
    mapping = {}
    for f in os.listdir(folder):
        if f.endswith(".tif") or f.endswith(".tiff"):
            ym = parse_year_month(f)
            if ym:
                mapping[ym] = os.path.join(folder, f)
    return mapping

# -----------------------------------------------------------
# Geometry Helpers
# -----------------------------------------------------------
def get_h3_sample_points(hex_geom):
    """Tạo 7 điểm sample cho 1 ô H3 (1 centroid + 6 midpoints)"""
    pts = []
    c = hex_geom.centroid
    pts.append((c.x, c.y))
    
    # Midpoint của 6 cạnh
    if hex_geom.geom_type == 'Polygon':
        coords = list(hex_geom.exterior.coords)
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            pts.append(((x1 + x2) / 2, (y1 + y2) / 2))
    return pts

def load_h3_multipoints(h3_path, crs_metric, crs_wgs84):
    """
    Load H3 grid và trả về dữ liệu hình học cần thiết
    """
    if not os.path.exists(h3_path):
        raise FileNotFoundError(f"Không tìm thấy file Grid: {h3_path}")

    print(f"loading grid: {h3_path}")
    h3 = gpd.read_file(h3_path)
    
    # Chuyển đổi CRS để tính toán hình học chính xác
    h3_metric = h3.to_crs(crs_metric)
    h3_wgs = h3_metric.to_crs(crs_wgs84)
    
    h3_ids = h3["h3_index"].tolist()
    
    # Tạo point groups cho sampling
    point_groups = [get_h3_sample_points(geom) for geom in h3_wgs.geometry]
    
    return h3_ids, point_groups, list(h3_wgs.geometry)

def random_points_in_polygon(poly, n):
    """Sinh n điểm ngẫu nhiên nằm trong polygon"""
    minx, miny, maxx, maxy = poly.bounds
    points = []
    while len(points) < n:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if poly.contains(p):
            points.append((p.x, p.y))
    return points

# -----------------------------------------------------------
# Sampling Logic
# -----------------------------------------------------------
def is_nodata(value, nodata):
    if value is None or nodata is None:
        return value is None
    try:
        return math.isclose(float(value), float(nodata), rel_tol=1e-9, abs_tol=1e-9)
    except (ValueError, TypeError):
        return value == nodata

def sample_multiband_robust(tif_path, point_groups, h3_geoms=None, n_random=15):
    """
    Chiến thuật lấy mẫu: 
    1. Lấy tại tâm
    2. Lấy trung bình 6 điểm cạnh
    3. Lấy random trong vùng (fallback)
    """
    with rasterio.open(tif_path) as src:
        nodata = src.nodata
        num_bands = src.count
        num_cells = len(point_groups)
        
        # Mảng kết quả [num_cells][num_days_in_month]
        vals = [[None] * num_bands for _ in range(num_cells)]

        for band_idx in range(num_bands):
            idx_param = band_idx + 1 # rasterio index bắt đầu từ 1
            
            for i, points in enumerate(point_groups):
                # Strategy 1: Centroid
                try:
                    v = next(src.sample([points[0]], indexes=idx_param))[0]
                    if not is_nodata(v, nodata):
                        vals[i][band_idx] = float(v)
                        continue
                except: pass

                # Strategy 2: 6 midpoints
                valid_vals = []
                for pt in points[1:]:
                    try:
                        v = next(src.sample([pt], indexes=idx_param))[0]
                        if not is_nodata(v, nodata):
                            valid_vals.append(v)
                    except: pass
                
                if valid_vals:
                    vals[i][band_idx] = float(sum(valid_vals) / len(valid_vals))
                    continue

                # Strategy 3: Random points (slowest, fallback)
                if h3_geoms is not None:
                    rand_pts = random_points_in_polygon(h3_geoms[i], n_random)
                    rand_vals = []
                    for pt in rand_pts:
                        try:
                            v = next(src.sample([pt], indexes=idx_param))[0]
                            if not is_nodata(v, nodata):
                                rand_vals.append(v)
                        except: pass
                    
                    if rand_vals:
                        vals[i][band_idx] = float(sum(rand_vals) / len(rand_vals))

        return vals, nodata