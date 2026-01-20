# extract_rain_h3.py
import os
import pandas as pd
from datetime import datetime, timedelta

from config import DATA_RAW, DATA_OUT, CRS_WGS84, CRS_METRIC
from utils_h3 import index_files, load_h3_multipoints, sample_multiband_robust

# ============================================================
# PATH
# ============================================================
RAIN_DIR = os.path.join(DATA_RAW, "daily_rain")
H3_GRID  = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")
OUT_CSV  = os.path.join(DATA_OUT, "h3_rain_daily.csv")

# ============================================================
# LOAD H3 GRID + SAMPLE POINTS (7 điểm/cell)
# ============================================================
print("🔍 Load H3 grid và tạo sample points...")
h3_ids, point_groups = load_h3_multipoints(H3_GRID, CRS_METRIC, CRS_WGS84)
print(f"✅ {len(h3_ids)} H3 cells × 7 points")

# ============================================================
# INDEX FILES
# ============================================================
rain_map = index_files(RAIN_DIR)
print(f"📁 Tìm thấy {len(rain_map)} files")

# ============================================================
# EXTRACT
# ============================================================
records = []

# --- SỬA Ở ĐÂY: Thêm hàm sorted() ---
# sorted() sẽ tự động sắp xếp key (year, month) từ nhỏ đến lớn
# (2022, 1) -> (2022, 2) -> ... -> (2022, 10)
sorted_items = sorted(rain_map.items())

for (year, month), tif_path in sorted_items:
    print(f"🌧️  Rain {year}-{month:02d}")
    
    # Sample với fallback strategy
    vals, nodata = sample_multiband_robust(tif_path, point_groups)
    num_days = len(vals[0]) if vals and vals[0] else 0
    
    for d in range(num_days):
        date = datetime(year, month, 1) + timedelta(days=d)
        for i, h3_id in enumerate(h3_ids):
            records.append({
                "h3_index": h3_id,
                "date": date.strftime("%Y-%m-%d"),
                "rain_mm": vals[i][d]
            })
# ============================================================
# SAVE
# ============================================================
df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False)

print("\n✅ HOÀN TẤT")
print(f"📄 File: {OUT_CSV}")
print(f"📊 Tổng dòng: {len(df)}")
print(f"⚠️  NoData: {df['rain_mm'].isna().sum()} ({df['rain_mm'].isna().mean()*100:.1f}%)")