import os
import geopandas as gpd
import matplotlib.pyplot as plt

from config import (
    CRS_WGS84,
    PATH_SHP_BOUNDARY,
    DATA_OUT
)

# ============================================================
# CONFIG
# ============================================================
PATH_H3 = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")

# 👉 DÁN H3 INDEX CẦN KIỂM TRA Ở ĐÂY (None nếu không dùng)
H3_HIGHLIGHT = "8765a3ae2ffffff"   # ví dụ
# H3_HIGHLIGHT = None

print("📂 Boundary:", PATH_SHP_BOUNDARY)
print("📂 H3 grid :", PATH_H3)

# ============================================================
# LOAD DATA
# ============================================================
boundary = gpd.read_file(PATH_SHP_BOUNDARY).to_crs(CRS_WGS84)
h3_grid = gpd.read_file(PATH_H3).to_crs(CRS_WGS84)

print(f"✅ Boundary polygons: {len(boundary)}")
print(f"✅ H3 cells          : {len(h3_grid)}")

# ============================================================
# TÁCH H3 CELL CẦN HIGHLIGHT
# ============================================================
h3_highlight = None

if H3_HIGHLIGHT is not None:
    if "h3_index" not in h3_grid.columns:
        raise ValueError("❌ Không tìm thấy cột 'h3_index' trong H3 grid")

    h3_highlight = h3_grid[h3_grid["h3_index"] == H3_HIGHLIGHT]

    if h3_highlight.empty:
        print(f"⚠️ Không tìm thấy H3 index: {H3_HIGHLIGHT}")
    else:
        print(f"⭐ Highlight H3 index: {H3_HIGHLIGHT}")

# ============================================================
# PLOT
# ============================================================
fig, ax = plt.subplots(figsize=(10, 12))

# 1️⃣ Vẽ toàn bộ H3 grid (nền)
h3_grid.plot(
    ax=ax,
    facecolor="none",
    edgecolor="orange",
    linewidth=0.3,
    alpha=0.6
)

# 2️⃣ Vẽ H3 được chọn (nổi bật)
if h3_highlight is not None and not h3_highlight.empty:
    h3_highlight.plot(
        ax=ax,
        facecolor="red",
        edgecolor="darkred",
        linewidth=1.5,
        alpha=0.7,
        label="Selected H3 cell"
    )

# 3️⃣ Vẽ boundary
boundary.plot(
    ax=ax,
    facecolor="none",
    edgecolor="black",
    linewidth=1.2
)

# ============================================================
# STYLE
# ============================================================
ax.set_title("H3 Grid phủ Đồng bằng sông Cửu Long", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")

if h3_highlight is not None and not h3_highlight.empty:
    ax.legend()

plt.tight_layout()
plt.show()

print("✅ Hiển thị bản đồ xong")
