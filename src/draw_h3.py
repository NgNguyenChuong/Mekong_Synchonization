import os
import geopandas as gpd
import matplotlib.pyplot as plt

from config import (
    CRS_WGS84,
    PATH_SHP_BOUNDARY,
    DATA_OUT
)

# ============================================================
# PATH
# ============================================================
PATH_H3 = os.path.join(DATA_OUT, "h3_grid_dbscl.geojson")

print("📂 Boundary:", PATH_SHP_BOUNDARY)
print("📂 H3 grid:", PATH_H3)

# ============================================================
# LOAD DATA
# ============================================================
boundary = gpd.read_file(PATH_SHP_BOUNDARY).to_crs(CRS_WGS84)
h3_grid = gpd.read_file(PATH_H3).to_crs(CRS_WGS84)

print(f"✅ Boundary polygons: {len(boundary)}")
print(f"✅ H3 cells: {len(h3_grid)}")

# ============================================================
# PLOT
# ============================================================
fig, ax = plt.subplots(figsize=(10, 12))

# Vẽ H3 trước (nền)
h3_grid.plot(
    ax=ax,
    facecolor="none",
    edgecolor="orange",
    linewidth=0.3
)

# Vẽ boundary đè lên
boundary.plot(
    ax=ax,
    facecolor="none",
    edgecolor="black",
    linewidth=1.2
)

ax.set_title("H3 Grid phủ Đồng bằng sông Cửu Long", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")

plt.tight_layout()
plt.show()
print("✅ Hiển thị bản đồ xong")