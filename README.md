# H3 Geo Pipeline (Generalized)

This project converts daily raster climate data into H3 time series for any region.

The workflow is now generalized:
- You can place your own boundary shapefile in `data/raw`.
- You can place your own raster datasets in `data/raw/<dataset_folder>`.
- Run `src/pipeline.py` to generate:
`data/processed/h3_grid.geojson` and per-dataset H3 CSV outputs.

## 0. Setup environment

Recommended Python version: `3.13.5`

Using a virtual environment is strongly recommended to avoid dependency conflicts.

Create virtual environment:

```bash
# Windows
python -m venv env

# macOS/Linux
python3 -m venv env
```

Activate virtual environment:

```bash
# Windows (PowerShell)
.\env\Scripts\Activate.ps1

# Windows (CMD)
env\Scripts\activate.bat

# macOS/Linux
source env/bin/activate
```

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Input Structure

### Boundary shapefile
Provide exactly one `.shp` file in `data/raw`.

Required sidecar files usually include `.dbf`, `.shx`, `.prj` in the same folder.

### Raster datasets
By default, these folders are expected (can be customized with `dataset_specs.json`):
- `data/raw/daily_rain`
- `data/raw/daily_solar`
- `data/raw/daily_temp_avg`
- `data/raw/daily_temp_max`
- `data/raw/daily_temp_min`
- `data/raw/daily_humid`

Raster filename must contain `YYYY_M` or `YYYY_MM` so the pipeline can map year-month.

Example:
- `rain_2024_01.tif`
- `temp_2025_7.tif`

## 3. Optional Dataset Customization

Create `data/raw/dataset_specs.json` to override default dataset config.

Example:

```json
{
	"rain": {
		"folder": "daily_rain",
		"col_name": "rain_mm",
		"output_file": "h3_rain_daily_filled.csv"
	},
	"wind": {
		"folder": "daily_wind",
		"col_name": "wind_mps",
		"output_file": "h3_wind_daily_filled.csv"
	}
}
```

## 4. Run Pipeline

```bash
python src/pipeline.py
```

Pipeline steps:
1. Resolve input boundary shapefile.
2. Clean/dissolve boundary (optional small island filtering).
3. Build H3 grid clipped to boundary.
4. Extract daily raster values for each H3 cell.
5. Fill missing values (spatial + nearest-neighbor fallback).
6. Save each dataset CSV and merge to final file.

## 5. Outputs

- `data/processed/h3_grid.geojson`
- `data/processed/h3_<dataset>_daily_filled.csv`
- `data/processed/FINAL_MERGED_DATASET.csv`

## 6. Important Environment Variables

- `H3_RESOLUTION`: H3 resolution (default `7`)
- `BUFFER_DIST`: boundary buffer in meters before polyfill (default `0`)
- `MIN_ISLAND_AREA_KM2`: remove tiny polygons below this area (default `0`)
- `ENABLE_GEE_FALLBACK`: `true/false` (default `false`)

## 7. Optional GEE Fallback

If no local shapefile is available, you can enable automatic download from Google Earth Engine:

- Set `ENABLE_GEE_FALLBACK=true`
- Optionally configure:
`GEE_PROJECT`, `GEE_ADMIN_COLLECTION`, `GEE_ADMIN_NAME_FIELD`, `GEE_TARGET_AREAS` in `src/config.py`

Local shapefile in `data/raw` still has higher priority when present.

