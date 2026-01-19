# src/config.py
import os

# --- CẤU HÌNH KHÔNG GIAN ---
H3_RES = 7
CRS_WGS84 = "EPSG:4326"    # Kinh/Vĩ độ (cho H3)
CRS_METRIC = "EPSG:32648"  # UTM Zone 48N (cho Buffer mét)
BUFFER_DIST = 2441.2 # Buffer 2km để bắt mép biển

# --- ĐƯỜNG DẪN DỮ LIỆU ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(BASE_DIR, "data", "raw")
DATA_OUT = os.path.join(BASE_DIR, "data", "processed")

# File đầu vào cụ thể (Sửa tên file khớp với máy bạn)
PATH_SHP_BOUNDARY = os.path.join(DATA_RAW, "DBSCL_Boundary.shp")
PATH_DEM = os.path.join(DATA_RAW, "DEM_DBSCL.tif")
PATH_LANDCOVER = os.path.join(DATA_RAW, "LAND_COVER.tif")
PATH_WATER_CSV = os.path.join(DATA_RAW, "water_level.csv")

# Thư mục chứa file ảnh động (ERA5/CHIRPS)
DIR_RAIN = os.path.join(DATA_RAW, "daily_rain")
DIR_TEMP = os.path.join(DATA_RAW, "daily_temp")
HUMID_DIR = os.path.join(DATA_RAW, "daily_humid")
RAD_DIR   = os.path.join(DATA_RAW, "daily_radiation")
# Đảm bảo thư mục đầu ra tồn tại
os.makedirs(DATA_OUT, exist_ok=True)