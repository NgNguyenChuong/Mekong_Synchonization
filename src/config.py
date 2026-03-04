import os

# ============================================================
# PATH SETTINGS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_RAW = os.path.join(DATA_DIR, "raw")
DATA_PROCESSED = os.path.join(DATA_DIR, "processed")

# Create directories if they don't exist
os.makedirs(DATA_RAW, exist_ok=True)
os.makedirs(DATA_PROCESSED, exist_ok=True)

# --- SHAPEFILE & GRID PATHS ---
# Raw shapefile downloaded from GEE
SHAPEFILE_RAW = os.path.join(DATA_RAW, "DBSCL_Boundary_Raw.shp")
# Cleaned shapefile (islands removed)
SHAPEFILE_CLEAN = os.path.join(DATA_RAW, "DBSCL_Boundary_Clean.shp")
# Final H3 Grid
H3_GRID_GEOJSON = os.path.join(DATA_PROCESSED, "h3_grid_dbscl.geojson")

# ============================================================
# GEOSPATIAL SETTINGS
# ============================================================
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:32648"  # UTM Zone 48N for accurate area calculation in Vietnam
BUFFER_DIST = 2000         # 2km buffer for grid generation
MIN_ISLAND_AREA_KM2 = 600  # Threshold to remove small islands (keeps Phu Quoc)
H3_RESOLUTION = 7          # H3 Resolution

# GEE Project ID (Replace with your actual project ID)
GEE_PROJECT = 'geemap-mekong-483717' 

# Target Provinces for Mekong Delta
MEKONG_PROVINCES = [
    'An Giang', 'Bac Lieu', 'Ben Tre', 'Ca Mau', 'Can Tho city',
    'Dong Thap', 'Hau Giang', 'Kien Giang', 'Long An',
    'Soc Trang', 'Tien Giang', 'Tra Vinh', 'Vinh Long'
]

# ============================================================
# DATASET SPECIFICATIONS
# ============================================================
DATA_SPECS = {
    "rain": {
        "folder": "daily_rain",
        "col_name": "rain_mm",
        "output_file": "h3_rain_daily_filled.csv"
    },
    "solar": {
        "folder": "daily_solar",
        "col_name": "solar",
        "output_file": "h3_solar_daily_filled.csv"
    },
    "temp_avg": {
        "folder": "daily_temp_avg",
        "col_name": "temp_c",
        "output_file": "h3_temp_daily_filled.csv"
    },
    "temp_max": {
        "folder": "daily_temp_max",
        "col_name": "temp_max_c",
        "output_file": "h3_temp_max_daily_filled.csv"
    },
    "temp_min": {
        "folder": "daily_temp_min",
        "col_name": "temp_min_c",
        "output_file": "h3_temp_min_daily_filled.csv"
    },
    "humidity": {
        "folder": "daily_humid",
        "col_name": "rh_percent",
        "output_file": "h3_rh_daily_filled.csv"
    }
}

FILL_CONFIG = {
    "MAX_K": 3,
    "MIN_NEI": 3
}