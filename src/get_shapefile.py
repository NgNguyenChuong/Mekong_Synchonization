import ee
import geemap
import os

# 1. Init GEE
ee.Initialize(project='geemap-mekong-483717')

# 2. Danh sách 13 tỉnh ĐBSCL
mekong_provinces = [
    'An Giang', 'Bac Lieu', 'Ben Tre', 'Ca Mau', 'Can Tho city',
    'Dong Thap', 'Hau Giang', 'Kien Giang', 'Long An',
    'Soc Trang', 'Tien Giang', 'Tra Vinh', 'Vinh Long'
]

# 3. Lấy boundary từ GAUL
vietnam = ee.FeatureCollection("FAO/GAUL/2015/level1")
dbscl_fc = vietnam.filter(
    ee.Filter.inList('ADM1_NAME', mekong_provinces)
)

# 4. Thư mục output
OUT_DIR = r"D:\hackathon\Mekong_DGGS\data\raw"
os.makedirs(OUT_DIR, exist_ok=True)

# 5. Export shapefile
geemap.ee_export_vector(
    dbscl_fc,
    filename=os.path.join(OUT_DIR, "DBSCL_Boundary.shp")
)

print("✅ Đã export shapefile ĐBSCL")
