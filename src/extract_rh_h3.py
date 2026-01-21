# extract_rh_h3.py
import os
import pandas as pd
from datetime import datetime, timedelta

# Import config và utils
from config import DATA_RAW, DATA_OUT, CRS_WGS84, CRS_METRIC
from utils_h3 import index_files, load_h3_multipoints, sample_multiband_robust

# ============================================================
# PATH
# ============================================================
# 1. Thay đổi đường dẫn đến thư mục chứa file Độ ẩm
RH_DIR = os.path.join(DATA_RAW, "daily_humid") 

# 2. File Grid (Giữ nguyên)
H3_GRID  = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")

# 3. Thay đổi tên file CSV đầu ra
OUT_CSV  = os.path.join(DATA_OUT, "h3_rh_daily.csv")

# ============================================================
# LOAD H3 GRID + SAMPLE POINTS (7 điểm/cell)
# ============================================================
print("🔍 Load H3 grid và tạo sample points...")
h3_ids, point_groups,h3_geoms = load_h3_multipoints(H3_GRID, CRS_METRIC, CRS_WGS84)
print(f"✅ {len(h3_ids)} H3 cells × 7 points")

# ============================================================
# INDEX FILES
# ============================================================
# Hàm index_files vẫn hoạt động tốt với tên file kiểu "3_RH_ERA5_2022_01.tif"
# vì nó tìm chuỗi "2022_01" bằng regex.
rh_map = index_files(RH_DIR)
print(f"📁 Tìm thấy {len(rh_map)} files độ ẩm")

# ============================================================
# EXTRACT
# ============================================================
records = []

# Sắp xếp theo thời gian (Tháng 1 -> Tháng 12)
sorted_items = sorted(rh_map.items())

for (year, month), tif_path in sorted_items:
    print(f"💧 RH (Humidity) {year}-{month:02d}")
    
    # Sample với fallback strategy (7 điểm)
    vals, nodata = sample_multiband_robust(tif_path, point_groups,
    h3_geoms,
    n_random=15)
    
    # Kiểm tra số ngày trong file (số band)
    num_days = len(vals[0]) if vals and vals[0] else 0
    
    for d in range(num_days):
        # Tính ngày thực tế
        date = datetime(year, month, 1) + timedelta(days=d)
        
        for i, h3_id in enumerate(h3_ids):
            records.append({
                "h3_index": h3_id,
                "date": date.strftime("%Y-%m-%d"),
                
                # --- SỬA Ở ĐÂY: Tên cột là rh_percent ---
                "rh_percent": vals[i][d]  
            })

# ============================================================
# SAVE
# ============================================================
df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False)

print("\n✅ HOÀN TẤT")
print(f"📄 File: {OUT_CSV}")
print(f"📊 Tổng dòng: {len(df)}")

# Kiểm tra NoData cho cột rh_percent
if 'rh_percent' in df.columns:
    missing = df['rh_percent'].isna().sum()
    percent = df['rh_percent'].isna().mean() * 100
    print(f"⚠️  NoData: {missing} ({percent:.1f}%)")