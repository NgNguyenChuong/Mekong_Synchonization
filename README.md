# 🌏 Mekong DGGS - H3 Geospatial Pipeline

<p align="center">
  <strong>Transform Climate & Geospatial Data into H3 Hexagonal Grid Format</strong><br>
  <em>Designed for Mekong Delta Region Analysis</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/H3-Resolution%207-00A67E?style=flat-square" alt="H3">
  <img src="https://img.shields.io/badge/Parallel-ProcessPool-FF6B6B?style=flat-square" alt="Parallel">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

---

## 🎯 What is this?

**Mekong_DGGS** converts raster climate data (GeoTIFF) and vector boundaries (Shapefiles) into structured time-series data indexed by [Uber H3](https://h3geo.org/) hexagonal cells.

**Use cases:**
- Climate modeling for flood/drought prediction
- Agricultural planning with spatial-temporal data
- Environmental monitoring dashboards
- Machine learning feature engineering

---

## ⚡ Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/your-repo/Mekong_DGGS.git
cd Mekong_DGGS

# 2. Create virtual environment
python -m venv env
.\env\Scripts\Activate.ps1   # Windows
# source env/bin/activate    # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run pipeline
python main.py
```

---

## 📊 Data Types Supported

| Type | Description | Example | Output |
|------|-------------|---------|--------|
| **Dynamic** | Daily time series | Rain, Temperature, Humidity | `FINAL_MERGED_DATASET.csv` |
| **Static** | One-time features | DEM, Land Cover, River Distance | `DIM_H3_STATIC.csv` |
| **Periodic** | Satellite imagery | Sentinel-2 NDVI/NDWI | `PERIODIC_MERGED.csv` |

---

## 🗂️ Input Data Structure

```
data/raw/
├── boundary_input.shp           # Required: region boundary
├── daily_rain/                  # Dynamic datasets
│   ├── 2024_01.tif             # Format: {year}_{month}.tif
│   └── 2024_02.tif             # Each band = 1 day
├── daily_temp_avg/
├── daily_humid/
├── daily_solar/
├── dem/
│   └── DEM_DBSCL.tif           # Static: elevation
├── landcover/
│   └── LandCover_DBSCL_2021.tif
├── river/
│   └── River_DBSCL.tif
└── sentinel2_ndvi/              # Periodic: satellite
    ├── NDVI_2024-01-15.tif
    └── NDWI_2024-01-15.tif
```

---

## 🏗️ Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  PREPROCESSING: Shapefile → Clean → H3 Grid (h3_grid.geojson)│
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              PARALLEL PROCESSING (Multi-core)                 │
│  ┌────────────┐    ┌────────────┐    ┌────────────────┐      │
│  │  DYNAMIC   │    │   STATIC   │    │    PERIODIC    │      │
│  │ Rain, Temp │    │ DEM, Land  │    │ NDVI, NDWI     │      │
│  │ Humidity   │    │ River Dist │    │ (Satellite)    │      │
│  └────────────┘    └────────────┘    └────────────────┘      │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│  OUTPUTS: CSV files with H3 index + temporal/spatial values   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Extraction Methods

### Point Sampling (Dynamic Data)
```
    H3 He_______.______ xagon
        ╱              ╲
       .                .
      ╱                  ╲    . cen = Centroid (primary sampling point)
     ╱          . cen     ╲   If NoData → fallback to 6 edge midpoints
     ╲                    ╱
      .                  .
       ╲                ╱
        ╲_______.______╱
```

### Zonal Statistics (Static Data)

| Method | Use Case | Description |
|--------|----------|-------------|
| `mean` | DEM | Average value in hexagon |
| `all_classes` | Land Cover | % of each class per cell |
| `min_distance` | River | Distance to nearest river (km) |

### Gap Filling Strategy
1. **K-Ring Spatial** → Average of neighboring H3 cells
2. **KDTree Nearest** → Copy from closest valid cell
3. **Temporal Interpolation** → Linear fill for time series

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `H3_RESOLUTION` | 7 | Grid resolution (0-15), 7 ≈ 5.16 km² |
| `BUFFER_DIST` | 0 | Boundary buffer (meters) |
| `MIN_ISLAND_AREA_KM2` | 0 | Remove small islands |

### Custom Dataset Specs

Create JSON files in `data/raw/` to override defaults:

- `dataset_specs.json` - Dynamic datasets
- `static_specs.json` - Static datasets  
- `periodic_specs.json` - Periodic datasets

Example:
```json
{
  "sentinel_ndvi": {
    "folder": "sentinel2_ndvi",
    "file_pattern": "NDVI_{date}.tif",
    "date_pattern": "%Y-%m-%d",
    "col_name": "ndvi",
    "output_file": "h3_sentinel_ndvi.csv",
    "method": "mean"
  }
}
```

---

## 📁 Project Structure

```
Mekong_DGGS/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── src/
│   ├── config.py            # Configuration & specs
│   ├── preprocessing.py     # H3 grid generation
│   ├── processing.py        # Data extraction & merge
│   ├── utils_h3.py          # H3 utilities
│   └── add_on_component/    # Additional tools
│       ├── getWaterLevel.py # MRC water level API
│       └── format_*.py      # Data formatters
├── data/
│   ├── raw/                 # Input data
│   ├── processed/           # Output data
│   └── water/               # Water level data
├── notebooks/               # Data download notebooks
└── scripts/                 # Utility scripts
```

---

## 📦 Output Files

```
data/processed/
├── h3_grid.geojson              # H3 hexagonal grid geometry
├── h3_rain_daily_filled.csv     # Individual dataset outputs
├── h3_temp_daily_filled.csv
├── h3_dem.csv
├── h3_landcover.csv
├── FINAL_MERGED_DATASET.csv     # ← All dynamic data merged
├── DIM_H3_STATIC.csv            # ← All static features
└── PERIODIC_MERGED.csv          # ← All periodic data
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---------|---------|
| **h3** | Hexagonal grid indexing |
| **geopandas** | Vector data processing |
| **rasterio** | GeoTIFF I/O |
| **rasterstats** | Zonal statistics |
| **scipy** | KDTree spatial search |
| **pandas** | Data manipulation |
| **numpy** | Numerical operations |

---

## 📖 Notebooks

| Notebook | Purpose |
|----------|---------|
| `DBSCL_Data_Download_*.ipynb` | Download climate data |
| `DBSCL_Sentinel.ipynb` | Download Sentinel-2 imagery |
| `get_data_DBSH.ipynb` | Data acquisition scripts |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built for Mekong Delta Climate Research 🌾</strong>
</p>
