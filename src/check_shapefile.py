import geopandas as gpd
import matplotlib.pyplot as plt
import os

# ============================================================
# PATH
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_SHP = os.path.join(BASE_DIR, "data", "raw", "DBSCL_Boundary_Clean.shp")

print("📂 Đọc shapefile:", PATH_SHP)

# ============================================================
# READ SHAPEFILE
# ============================================================
gdf = gpd.read_file(PATH_SHP)

print("✅ Đọc thành công")
print("CRS:", gdf.crs)
print("Số polygon:", len(gdf))

# ============================================================
# PLOT
# ============================================================
fig, ax = plt.subplots(figsize=(8, 10))

gdf.plot(
    ax=ax,
    edgecolor="black",
    facecolor="lightblue",
    linewidth=0.8
)

ax.set_title("Ranh giới 13 tỉnh Đồng bằng sông Cửu Long", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")

plt.tight_layout()
plt.show()
print("✅ Hiển thị bản đồ xong")