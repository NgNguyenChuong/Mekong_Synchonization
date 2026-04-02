#!/usr/bin/env python
"""Visualize one daily GeoTIFF band and the corresponding H3-assigned result for the same day."""

import argparse
import os
import sys
from datetime import datetime

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import Normalize
from rasterio.plot import plotting_extent


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED, H3_GRID_GEOJSON  # noqa: E402
from src.utils_h3 import index_files  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize one daily raster band and its H3-assigned values")
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format")
    parser.add_argument("--folder", default="daily_temp_max", help="Raw folder name containing monthly multi-band tif files")
    parser.add_argument("--csv", default="h3_temp_max_daily_filled.csv", help="Processed CSV containing H3 daily assignments")
    parser.add_argument("--col", default=None, help="Value column name in the CSV. If omitted, it will be inferred.")
    parser.add_argument("--tif", default=None, help="Optional direct path to a tif file. If omitted, the script auto-finds the monthly file.")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "daily_h3_day.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def guess_value_column(df):
    excluded = {"h3_index", "date"}
    candidates = [c for c in df.columns if c not in excluded]
    if not candidates:
        raise ValueError("Không tìm được cột giá trị trong CSV.")
    return candidates[0]


def find_month_tif(folder_path, target_date):
    file_map = index_files(folder_path)
    if not file_map:
        raise FileNotFoundError(f"Không tìm thấy file .tif nào trong: {folder_path}")

    key = (target_date.year, target_date.month)
    tif_path = file_map.get(key)
    if not tif_path:
        raise FileNotFoundError(
            f"Không tìm thấy tif cho tháng {target_date.year}_{target_date.month:02d} trong {folder_path}"
        )
    return tif_path


def load_h3_grid():
    if not os.path.exists(H3_GRID_GEOJSON):
        raise FileNotFoundError(f"Không tìm thấy file: {H3_GRID_GEOJSON}")
    gdf = gpd.read_file(H3_GRID_GEOJSON)
    gdf["h3_index"] = gdf["h3_index"].astype(str)
    return gdf


def load_daily_csv(csv_name):
    csv_path = os.path.join(DATA_PROCESSED, csv_name)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")
    return pd.read_csv(csv_path, dtype={"h3_index": str})


def build_output_paths(save_path):
    base, ext = os.path.splitext(save_path)
    if not ext:
        ext = ".png"
    return {
        "raster": f"{base}_raster{ext}",
        "h3": f"{base}_h3{ext}",
    }


def read_daily_band(tif_path, target_date):
    day_index = target_date.day
    with rasterio.open(tif_path) as src:
        if day_index > src.count:
            raise ValueError(
                f"File {os.path.basename(tif_path)} chỉ có {src.count} band, không có band cho ngày {target_date.day}."
            )
        data = src.read(day_index)
        extent = plotting_extent(src)
        nodata = src.nodata
    if nodata is not None:
        data = np.where(data == nodata, np.nan, data)
    return data, extent


def main():
    args = parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d")
    date_str = target_date.strftime("%Y-%m-%d")

    folder_path = os.path.join(DATA_RAW, args.folder)
    if args.tif:
        tif_path = args.tif
    else:
        tif_path = find_month_tif(folder_path, target_date)

    daily_df = load_daily_csv(args.csv)
    h3_grid = load_h3_grid()

    if "date" not in daily_df.columns:
        raise ValueError("CSV phải có cột date.")

    value_col = args.col or guess_value_column(daily_df)
    day_df = daily_df[daily_df["date"] == date_str].copy()
    if day_df.empty:
        raise ValueError(f"Không có dữ liệu cho ngày {date_str} trong {args.csv}")

    day_df = day_df[["h3_index", value_col]].copy()
    merged = h3_grid.merge(day_df, on="h3_index", how="left")

    tif_data, extent = read_daily_band(tif_path, target_date)

    raster_vals = tif_data[np.isfinite(tif_data)]
    h3_vals = merged[value_col].to_numpy(dtype=float)
    h3_vals = h3_vals[np.isfinite(h3_vals)]

    all_vals = []
    if raster_vals.size:
        all_vals.append(raster_vals)
    if h3_vals.size:
        all_vals.append(h3_vals)

    if all_vals:
        combined = np.concatenate(all_vals)
        vmin = float(np.nanmin(combined))
        vmax = float(np.nanmax(combined))
    else:
        vmin, vmax = 0.0, 1.0

    if vmin == vmax:
        vmax = vmin + 1.0

    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = "viridis"

    output_paths = build_output_paths(args.save)

    # Figure 1: raw daily raster
    fig1, ax1 = plt.subplots(figsize=(12, 9))
    ax1.imshow(tif_data, cmap=cmap, norm=norm, extent=extent, origin="upper")
    ax1.set_title(f"{os.path.basename(tif_path)} | band {target_date.day} | {date_str}")
    ax1.axis("off")

    sm1 = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm1.set_array([])
    cbar1 = fig1.colorbar(sm1, ax=ax1, fraction=0.03, pad=0.02)
    cbar1.set_label(value_col)

    plt.tight_layout()
    if args.save:
        os.makedirs(os.path.dirname(output_paths["raster"]), exist_ok=True)
        fig1.savefig(output_paths["raster"], dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {output_paths['raster']}")

    # Figure 2: H3-assigned values
    fig2, ax2 = plt.subplots(figsize=(12, 9))
    merged.plot(
        ax=ax2,
        column=value_col,
        cmap=cmap,
        norm=norm,
        linewidth=0.08,
        edgecolor="none",
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax2.set_title(f"H3 assigned values | {value_col} | {date_str}")
    ax2.axis("off")

    sm2 = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm2.set_array([])
    cbar2 = fig2.colorbar(sm2, ax=ax2, fraction=0.03, pad=0.02)
    cbar2.set_label(value_col)

    plt.tight_layout()
    if args.save:
        os.makedirs(os.path.dirname(output_paths["h3"]), exist_ok=True)
        fig2.savefig(output_paths["h3"], dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {output_paths['h3']}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
