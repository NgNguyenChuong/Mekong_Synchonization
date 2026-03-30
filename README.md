# 🌏 Mekong DGGS - H3 Geo Pipeline

<p align="center">
  <strong>Discrete Global Grid System Pipeline for Mekong Delta Climate Data</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/H3-Resolution%207-green.svg" alt="H3">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

---

## 📋 Overview

**Mekong_DGGS** is a geospatial data processing pipeline that converts raster climate data into H3 hexagonal grid time series. Designed for the **Mekong Delta (ĐBSCL)** region, this pipeline transforms GeoTIFF rasters and Shapefiles into structured tabular data for analysis and modeling.

### Key Features

- 🔷 **H3 Hexagonal Grid** - Resolution 7 (~5.16 km² per cell)
- ⚡ **Parallel Processing** - Multi-core extraction with ProcessPoolExecutor
- 🔄 **Smart Gap Filling** - K-Ring spatial + KDTree nearest neighbor fallback
- 📊 **Multi-data Support** - Dynamic, Static, and Periodic datasets

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PREPROCESSING                            │
│  Shapefile → Clean → Generate H3 Grid (h3_grid.geojson)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PARALLEL PROCESSING                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │   DYNAMIC    │  │    STATIC    │  │     PERIODIC     │       │
│  │  (Daily)     │  │  (One-time)  │  │  (Satellite)     │       │
│  │              │  │              │  │                  │       │
│  │ • Rain       │  │ • DEM        │  │ • Sentinel NDVI  │       │
│  │ • Temp       │  │ • Landcover  │  │ • Sentinel NDWI  │       │
│  │ • Humidity   │  │ • River      │  │                  │       │
│  │ • Solar      │  │              │  │                  │       │
│  └──────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           OUTPUTS                                │
│  • FINAL_MERGED_DATASET.csv  (Dynamic)                          │
│  • DIM_H3_STATIC.csv         (Static)                           │
│  • PERIODIC_MERGED.csv       (Periodic)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Setup Environment

**Recommended Python version:** `3.13.5`

```bash
# Create virtual environment
python -m venv env

# Activate (Windows PowerShell)
.\env\Scripts\Activate.ps1

# Activate (macOS/Linux)
source env/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare Data

Place your data in `data/raw/`:

```
data/raw/
├── boundary_input.shp          # Boundary shapefile (required)
├── boundary_input.dbf/.shx/.prj
├── daily_rain/                 # Dynamic: rainfall
│   ├── 2024_01.tif
│   └── 2024_02.tif
├── daily_temp_avg/             # Dynamic: temperature
├── daily_humid/                # Dynamic: humidity
├── daily_solar/                # Dynamic: solar radiation
├── dem/
│   └── DEM_DBSCL.tif           # Static: elevation
├── landcover/
│   └── LandCover_DBSCL_2021.tif # Static: land use
├── river/
│   └── River_DBSCL.tif         # Static: river proximity
└── sentinel2_ndvi/             # Periodic: satellite imagery
    ├── NDVI_2024-01-15.tif
    └── NDWI_2024-01-15.tif
```

### 4. Run Pipeline

```bash
python main.py
```

---

## 📊 Data Types

### Dynamic Data (Daily)

| Dataset   | Folder           | Column        | Description              |
|-----------|------------------|---------------|--------------------------|
| rain      | daily_rain       | rain_mm       | Rainfall (mm)            |
| temp_avg  | daily_temp_avg   | temp_c        | Average temperature (°C) |
| temp_max  | daily_temp_max   | temp_max_c    | Maximum temperature (°C) |
| temp_min  | daily_temp_min   | temp_min_c    | Minimum temperature (°C) |
| humidity  | daily_humid      | rh_percent    | Relative humidity (%)    |
| solar     | daily_solar      | solar         | Solar radiation          |

**File format:** `{year}_{month}.tif` with each band = 1 day

### Static Data (One-time)

| Dataset   | Method         | Output                          |
|-----------|----------------|---------------------------------|
| dem       | mean           | Average elevation per H3 cell   |
| landcover | all_classes    | % of each land class per cell   |
| river     | min_distance   | Distance to nearest river (km)  |

### Periodic Data (Satellite)

| Dataset       | Pattern           | Method | Description          |
|---------------|-------------------|--------|----------------------|
| sentinel_ndvi | NDVI_{date}.tif   | mean   | Vegetation index     |
| sentinel_ndwi | NDWI_{date}.tif   | mean   | Water index          |

---

## 🔧 Extraction Methods

### Point Sampling (Dynamic)

```
     H3 Hexagon Cell
          ╱╲
         ╱  ╲
        ╱ M2 ╲
       ╱──────╲
      ╱   M1   ╲
     ╱    ●     ╲ M3      ● = Centroid (primary)
    ╱   (C)     ╲         M = Midpoint (fallback)
    ╲           ╱
     ╲   M6   ╱
      ╲──────╱
       ╲ M5 ╱
        ╲  ╱
         ╲╱
          M4

Step 1: Sample at Centroid (C)
Step 2: If C = NoData → Average of 6 Midpoints (M1-M6)
```

### Zonal Statistics (Static)

| Method        | Use Case    | Description                           |
|---------------|-------------|---------------------------------------|
| mean/max/min  | DEM         | Basic zonal statistics                |
| all_classes   | Landcover   | Calculate % of each class in cell     |
| min_distance  | River       | KDTree search for nearest river pixel |

### Gap Filling Strategy

1. **K-Ring Spatial Fill** - Average of neighboring cells (K=1,2,3)
2. **KDTree Nearest** - Copy from geographically nearest valid cell
3. **Temporal Interpolate** - Linear interpolation for periodic data

---

## 💻 CLI Usage

### Basic Commands

```bash
# Run full pipeline
python main.py

# List detected datasets
python main.py --list-datasets

# Dry-run (show plan only)
python main.py --dry-run
```

### Date Filtering

```bash
# Single month
python main.py --month 2024-03

# Date range
python main.py --from 2024-01 --to 2024-06
```

### Processing Scope

```bash
# Skip specific dataset types
python main.py --skip-static
python main.py --skip-dynamic
python main.py --skip-periodic

# Run only periodic
python main.py --only-periodic
```

### Performance Options

```bash
# Select specific datasets
python main.py --datasets rain,solar,temp_avg

# Control processing
python main.py --no-fill          # Skip gap filling
python main.py --no-merge         # Skip merging outputs
python main.py --skip-preprocess  # Use existing H3 grid
python main.py --workers 4        # Set worker count
```

---

## 📁 Output Structure

```
data/processed/
├── h3_grid.geojson              # H3 hexagonal grid
├── h3_rain_daily_filled.csv     # Rain time series
├── h3_temp_daily_filled.csv     # Temperature time series
├── h3_rh_daily_filled.csv       # Humidity time series
├── h3_solar_daily_filled.csv    # Solar time series
├── h3_dem.csv                   # DEM statistics
├── h3_landcover.csv             # Land cover fractions
├── h3_river.csv                 # River proximity
├── h3_sentinel_ndvi.csv         # NDVI time series
├── h3_sentinel_ndwi.csv         # NDWI time series
├── FINAL_MERGED_DATASET.csv     # Merged dynamic data
├── DIM_H3_STATIC.csv            # Merged static data
└── PERIODIC_MERGED.csv          # Merged periodic data
```

---

## ⚙️ Configuration

### Environment Variables

| Variable            | Default | Description                      |
|---------------------|---------|----------------------------------|
| H3_RESOLUTION       | 7       | H3 grid resolution (0-15)        |
| BUFFER_DIST         | 0       | Boundary buffer in meters        |
| MIN_ISLAND_AREA_KM2 | 0       | Remove islands smaller than (km²)|
| ENABLE_GEE_FALLBACK | false   | Enable Google Earth Engine       |

### Custom Dataset Specs

Override defaults by creating JSON files in `data/raw/`:

- `dataset_specs.json` - Dynamic datasets
- `static_specs.json` - Static datasets
- `periodic_specs.json` - Periodic datasets

Example `periodic_specs.json`:

```json
{
  "sentinel_ndvi": {
    "folder": "sentinel2_ndvi",
    "file_pattern": "NDVI_{date}.tif",
    "date_pattern": "%Y-%m-%d",
    "col_name": "ndvi",
    "output_file": "h3_sentinel_ndvi.csv",
    "method": "mean",
    "fill_method": "interpolate",
    "typical_interval_days": 30
  }
}
```

---

## 📚 Project Structure

```
Mekong_DGGS/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── src/
│   ├── config.py           # Configuration & dataset specs
│   ├── preprocessing.py    # H3 grid generation
│   ├── processing.py       # Data extraction & merging
│   ├── utils_h3.py         # H3 utility functions
│   └── add_on_component/   # Additional modules
│       ├── getWaterLevel.py    # MRC water level API
│       ├── format_waterlevel.py
│       └── format_sealevel.py
├── data/
│   ├── raw/                # Input data
│   ├── processed/          # Output data
│   └── water/              # Water level data
└── notebooks/              # Jupyter notebooks for data download
```

---

## 🛠️ Technologies

| Library     | Purpose                            |
|-------------|------------------------------------|
| h3          | Hexagonal grid system              |
| geopandas   | Vector data processing             |
| rasterio    | GeoTIFF read/write                 |
| rasterstats | Zonal statistics                   |
| scipy       | KDTree spatial search              |
| pandas      | Tabular data processing            |
| numpy       | Numerical computation              |

---

## 📖 Documentation

For detailed technical documentation, see [DOCUMENTATION.md](DOCUMENTATION.md).

---

## 📝 License

This project is licensed under the MIT License.
