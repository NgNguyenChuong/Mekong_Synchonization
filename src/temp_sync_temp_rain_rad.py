import os
import re
import rasterio
import geopandas as gpd
import pandas as pd
from datetime import datetime, timedelta

from config import (
    DATA_RAW,
    DATA_OUT,
    CRS_WGS84,
    CRS_METRIC
)

# ============================================================
# PATH
# ============================================================
RAIN_DIR = os.path.join(DATA_RAW, "daily_rain")
TEMP_DIR = os.path.join(DATA_RAW, "daily_temp")
RAD_DIR  = os.path.join(DATA_RAW, "daily_radiation")

H3_GRID_PATH = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")
OUT_CSV = os.path.join(DATA_OUT, "h3_climate_daily.csv")

# ============================================================
# LOAD H3 GRID (CENTROID ĐÚNG CRS)
# ============================================================
print("🔍 Load H3 grid...")
h3 = gpd.read_file(H3_GRID_PATH)

h3_metric = h3.to_crs(CRS_METRIC)
h3["centroid"] = h3_metric.centroid.to_crs(CRS_WGS84)
points = [(p.x, p.y) for p in h3.centroid]

print(f"✅ {len(h3)} H3 cells")

# ============================================================
# HELPER
# ============================================================
def parse_year_month(fname):
    m = re.search(r"(\d{4})_(\d{1,2})", fname)
    if not m:
        raise ValueError(f"❌ Không đọc được năm-tháng từ {fname}")
    return int(m.group(1)), int(m.group(2))


def index_files(folder):
    """
    {(2022,1): filepath}
    """
    mapping = {}
    for f in os.listdir(folder):
        if f.endswith(".tif"):
            ym = parse_year_month(f)
            mapping[ym] = os.path.join(folder, f)
    return mapping


def sample_multiband(tif_path, points):
    with rasterio.open(tif_path) as src:
        data = list(src.sample(points))
        nodata = src.nodata
    return data, nodata


# ============================================================
# INDEX FILES
# ============================================================
rain_map = index_files(RAIN_DIR)
temp_map = index_files(TEMP_DIR)
rad_map  = index_files(RAD_DIR)

# ============================================================
# MAIN LOOP
# ============================================================
records = []

for (year, month), rain_path in rain_map.items():
    print(f"📦 Xử lý {year}-{month:02d}")

    if (year, month) not in temp_map or (year, month) not in rad_map:
        print("⚠️  Thiếu file temp hoặc radiation → bỏ qua")
        continue

    temp_path = temp_map[(year, month)]
    rad_path  = rad_map[(year, month)]

    rain_vals, rain_nodata = sample_multiband(rain_path, points)
    temp_vals, temp_nodata = sample_multiband(temp_path, points)
    rad_vals,  rad_nodata  = sample_multiband(rad_path, points)

    num_days = len(rain_vals[0])

    for d in range(num_days):
        date = datetime(year, month, 1) + timedelta(days=d)

        for i, h3_id in enumerate(h3["h3_index"]):
            r = rain_vals[i][d]
            t = temp_vals[i][d]
            s = rad_vals[i][d]

            records.append({
                "h3_index": h3_id,
                "date": date.strftime("%Y-%m-%d"),
                "rain_mm": None if r == rain_nodata else float(r),
                "temp_c":  None if t == temp_nodata else float(t),
                "solar_mj":None if s == rad_nodata else float(s)
            })

# ============================================================
# SAVE
# ============================================================
df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False)

print("\n✅ HOÀN TẤT")
print(f"📄 File: {OUT_CSV}")
print(f"📊 Tổng dòng: {len(df)}")
