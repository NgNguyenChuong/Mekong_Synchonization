#!/usr/bin/env python
"""Show H3 grid colored by dem_mean."""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED, H3_GRID_GEOJSON  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Show H3 grid by dem_mean")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "dem_h3.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def load_dem_csv():
    csv_path = os.path.join(DATA_PROCESSED, "h3_dem.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")
    df = pd.read_csv(csv_path, dtype={"h3_index": str})
    if "dem_mean" not in df.columns:
        raise ValueError("File h3_dem.csv không có cột dem_mean")
    return df


def load_h3_grid():
    if not os.path.exists(H3_GRID_GEOJSON):
        raise FileNotFoundError(f"Không tìm thấy file: {H3_GRID_GEOJSON}")
    gdf = gpd.read_file(H3_GRID_GEOJSON)
    gdf["h3_index"] = gdf["h3_index"].astype(str)
    return gdf


def main():
    args = parse_args()
    
    dem_df = load_dem_csv()
    h3_grid = load_h3_grid()
    h3_grid = h3_grid.merge(dem_df[["h3_index", "dem_mean"]], on="h3_index", how="left")

    vmin = h3_grid["dem_mean"].min()
    vmax = h3_grid["dem_mean"].max()
    norm = Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(12, 10))
    
    h3_grid.plot(
        ax=ax,
        column="dem_mean",
        cmap="terrain",
        norm=norm,
        linewidth=0.08,
        edgecolor="none",
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax.set_title("H3 grid by dem_mean")
    ax.axis("off")

    sm = plt.cm.ScalarMappable(cmap="terrain", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("dem_mean (meters)")

    plt.tight_layout()
    
    if args.save:
        os.makedirs(os.path.dirname(args.save), exist_ok=True)
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {args.save}")
    
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
