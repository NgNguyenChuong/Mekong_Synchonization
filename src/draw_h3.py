# # draw nodata hightlight
# import os
# import geopandas as gpd
# import matplotlib.pyplot as plt

# from config import (
#     CRS_WGS84,
#     PATH_SHP_BOUNDARY,
#     DATA_OUT
# )

# # ============================================================
# # CONFIG
# # ============================================================
# PATH_H3 = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")

# # 👉 DÁN H3 INDEX CẦN KIỂM TRA Ở ĐÂY (None nếu không dùng)
# H3_HIGHLIGHT = "8765a2300ffffff"   # ví dụ
# # H3_HIGHLIGHT = None

# print("📂 Boundary:", PATH_SHP_BOUNDARY)
# print("📂 H3 grid :", PATH_H3)

# # ============================================================
# # LOAD DATA
# # ============================================================
# boundary = gpd.read_file(PATH_SHP_BOUNDARY).to_crs(CRS_WGS84)
# h3_grid = gpd.read_file(PATH_H3).to_crs(CRS_WGS84)

# print(f"✅ Boundary polygons: {len(boundary)}")
# print(f"✅ H3 cells          : {len(h3_grid)}")

# # ============================================================
# # TÁCH H3 CELL CẦN HIGHLIGHT
# # ============================================================
# h3_highlight = None

# if H3_HIGHLIGHT is not None:
#     if "h3_index" not in h3_grid.columns:
#         raise ValueError("❌ Không tìm thấy cột 'h3_index' trong H3 grid")

#     h3_highlight = h3_grid[h3_grid["h3_index"] == H3_HIGHLIGHT]

#     if h3_highlight.empty:
#         print(f"⚠️ Không tìm thấy H3 index: {H3_HIGHLIGHT}")
#     else:
#         print(f"⭐ Highlight H3 index: {H3_HIGHLIGHT}")

# # ============================================================
# # PLOT
# # ============================================================
# fig, ax = plt.subplots(figsize=(10, 12))

# # 1️⃣ Vẽ toàn bộ H3 grid (nền)
# h3_grid.plot(
#     ax=ax,
#     facecolor="none",
#     edgecolor="orange",
#     linewidth=0.3,
#     alpha=0.6
# )

# # 2️⃣ Vẽ H3 được chọn (nổi bật)
# if h3_highlight is not None and not h3_highlight.empty:
#     h3_highlight.plot(
#         ax=ax,
#         facecolor="red",
#         edgecolor="darkred",
#         linewidth=1.5,
#         alpha=0.7,
#         label="Selected H3 cell"
#     )

# # 3️⃣ Vẽ boundary
# boundary.plot(
#     ax=ax,
#     facecolor="none",
#     edgecolor="black",
#     linewidth=1.2
# )

# # ============================================================
# # STYLE
# # ============================================================
# ax.set_title("H3 Grid phủ Đồng bằng sông Cửu Long", fontsize=14)
# ax.set_xlabel("Longitude")
# ax.set_ylabel("Latitude")
# ax.set_aspect("equal")

# if h3_highlight is not None and not h3_highlight.empty:
#     ax.legend()

# plt.tight_layout()
# plt.show()

# print("✅ Hiển thị bản đồ xong")




# DRAW NODATA 
import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from config import (
    CRS_WGS84,
    SHAPEFILE_CLEAN,
    DATA_PROCESSED
)

# ============================================================
# CONFIG PATHS
# ============================================================
PATH_H3_GRID = os.path.join(DATA_PROCESSED, "h3_grid_dbscl.geojson")
PATH_TEMP_CSV = os.path.join(DATA_PROCESSED, "h3_solar_daily_filled.csv") # File CSV nhiệt độ
print("📂 Boundary:", SHAPEFILE_CLEAN)
print("📂 H3 grid :", PATH_H3_GRID)
print("📂 Temp CSV:", PATH_TEMP_CSV)

# ============================================================
# 1. LOAD DATA
# ============================================================
# Đọc Shapefile ranh giới
boundary = gpd.read_file(SHAPEFILE_CLEAN).to_crs(CRS_WGS84)

# Đọc H3 Grid
h3_grid = gpd.read_file(PATH_H3_GRID).to_crs(CRS_WGS84)

# Đọc CSV Nhiệt độ
df_temp = pd.read_csv(PATH_TEMP_CSV)
df_temp = df_temp.replace(-9999.0, np.nan)
print(f"✅ Boundary polygons: {len(boundary)}")
print(f"✅ H3 cells (Grid)  : {len(h3_grid)}")
print(f"✅ CSV Rows         : {len(df_temp)}")

# ============================================================
# 2. TÌM NODATA CELLS
# ============================================================
# Lọc các dòng có solar là NaN (trống)
df_missing = df_temp[df_temp['solar'].isna()]

# Lấy danh sách các h3_index duy nhất bị lỗi
nodata_indices = df_missing['h3_index'].unique()

num_nodata = len(nodata_indices)
total_cells = len(h3_grid)
percent_nodata = (num_nodata / total_cells) * 100

print("-" * 30)
if num_nodata > 0:
    print(f"⚠️  PHÁT HIỆN NODATA!")
    print(f"🔴 Số lượng ô bị thiếu dữ liệu: {num_nodata} / {total_cells} ({percent_nodata:.2f}%)")
    print(f"📝 Danh sách 5 ô lỗi đầu tiên: {nodata_indices[:5]}")
else:
    print("✅ TUYỆT VỜI! Không có ô nào bị thiếu dữ liệu (NoData).")
print("-" * 30)

# ============================================================
# 3. TÁCH GRID ĐỂ VẼ
# ============================================================
# Tách GeoDataFrame thành 2 phần: Lỗi và Hợp lệ
h3_nodata_gdf = h3_grid[h3_grid['h3_index'].isin(nodata_indices)]
h3_valid_gdf  = h3_grid[~h3_grid['h3_index'].isin(nodata_indices)]

# ============================================================
# 4. PLOT BẢN ĐỒ
# ============================================================
fig, ax = plt.subplots(figsize=(12, 12))

# A. Vẽ Ranh giới (Boundary) - Nền dưới cùng
boundary.plot(
    ax=ax,
    facecolor="#f0f0f0", # Màu xám nhạt
    edgecolor="black",
    linewidth=1.0,
    alpha=0.5,
    label='Ranh giới ĐBSCL'
)

# B. Vẽ các ô Hợp lệ (Valid) - Màu xanh nhạt hoặc chỉ viền
if not h3_valid_gdf.empty:
    h3_valid_gdf.plot(
        ax=ax,
        facecolor="none",
        edgecolor="green",
        linewidth=0.1,
        alpha=0.3,
        # label='Valid Data' # Không cần label cho cái này đỡ rối
    )

# C. Vẽ các ô NoData (Lỗi) - Màu ĐỎ nổi bật
if not h3_nodata_gdf.empty:
    h3_nodata_gdf.plot(
        ax=ax,
        facecolor="red",
        edgecolor="darkred",
        linewidth=0.5,
        alpha=0.8,
        label=f'No Data ({num_nodata} cells)'
    )

# ============================================================
# STYLE & LEGEND
# ============================================================
ax.set_title(f"Kiểm tra chất lượng dữ liệu H3 (NoData Highlight)\nTotal Cells: {total_cells} | Missing: {num_nodata}", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")

# Tạo Legend thủ công để đẹp hơn
import matplotlib.patches as mpatches
legend_patches = [
    mpatches.Patch(facecolor='none', edgecolor='black', label='Ranh giới hành chính'),
    mpatches.Patch(facecolor='none', edgecolor='green', alpha=0.5, label='Có dữ liệu (Valid)'),
    mpatches.Patch(color='red', label='Thiếu dữ liệu (NoData)')
]
ax.legend(handles=legend_patches, loc='lower right')

plt.tight_layout()
plt.show()

print("✅ Đã hiển thị bản đồ kiểm tra.")