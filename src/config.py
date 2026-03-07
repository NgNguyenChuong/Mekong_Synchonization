import os
import json


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default

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
# Input boundary is required to be exactly one .shp in data/raw.
# Fallback output path when ENABLE_GEE_FALLBACK=true.
SHAPEFILE_RAW = os.path.join(DATA_RAW, "boundary_input.shp")

# Generated artifacts
VECTOR_WORK_DIR = os.path.join(DATA_PROCESSED, "vector")
os.makedirs(VECTOR_WORK_DIR, exist_ok=True)
SHAPEFILE_CLEAN = os.path.join(VECTOR_WORK_DIR, "boundary_clean.shp")
H3_GRID_GEOJSON = os.path.join(DATA_PROCESSED, "h3_grid.geojson")

# ============================================================
# GEOSPATIAL SETTINGS
# ============================================================
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:32648"  # UTM Zone 48N for accurate area calculation in Vietnam
BUFFER_DIST = _env_int("BUFFER_DIST", 0)  # meters
MIN_ISLAND_AREA_KM2 = _env_float("MIN_ISLAND_AREA_KM2", 0.0)
H3_RESOLUTION = _env_int("H3_RESOLUTION", 7)

# GEE fallback settings (disabled by default).
ENABLE_GEE_FALLBACK = _env_bool("ENABLE_GEE_FALLBACK", False)
GEE_PROJECT = os.getenv("GEE_PROJECT", "").strip()
GEE_ADMIN_COLLECTION = os.getenv("GEE_ADMIN_COLLECTION", "FAO/GAUL/2015/level1").strip()
GEE_ADMIN_NAME_FIELD = os.getenv("GEE_ADMIN_NAME_FIELD", "ADM1_NAME").strip()

# Default target names used only when GEE fallback is enabled.
GEE_TARGET_AREAS = [
    'An Giang', 'Bac Lieu', 'Ben Tre', 'Ca Mau', 'Can Tho city',
    'Dong Thap', 'Hau Giang', 'Kien Giang', 'Long An',
    'Soc Trang', 'Tien Giang', 'Tra Vinh', 'Vinh Long'
]

# ============================================================
# DATASET SPECIFICATIONS
# ============================================================
DEFAULT_DATA_SPECS = {
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

DATA_SPECS_OVERRIDE_FILE = os.path.join(DATA_RAW, "dataset_specs.json")


def load_data_specs():
    if not os.path.exists(DATA_SPECS_OVERRIDE_FILE):
        return DEFAULT_DATA_SPECS

    try:
        with open(DATA_SPECS_OVERRIDE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError(f"Invalid dataset spec file: {DATA_SPECS_OVERRIDE_FILE}. Error: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise ValueError(f"{DATA_SPECS_OVERRIDE_FILE} must be a non-empty object.")

    required_fields = {"folder", "col_name", "output_file"}
    for key, spec in data.items():
        if not isinstance(spec, dict):
            raise ValueError(f"Dataset '{key}' must be an object.")
        missing = required_fields - set(spec.keys())
        if missing:
            raise ValueError(f"Dataset '{key}' is missing required fields: {sorted(missing)}")

    return data


DATA_SPECS = load_data_specs()

FILL_CONFIG = {
    "MAX_K": 3,
    "MIN_NEI": 3
}