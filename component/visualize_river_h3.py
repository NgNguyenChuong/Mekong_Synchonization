#!/usr/bin/env python
"""Show H3 grid colored by river_proximity_fraction."""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED, H3_GRID_GEOJSON  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Show H3 grid by river_proximity_fraction")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "river_h3.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def load_river_csv():
    csv_path = os.path.join(DATA_PROCESSED, "h3_river.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")
    df = pd.read_csv(csv_path, dtype={"h3_index": str})
    if "river_proximity_fraction" not in df.columns:
        raise ValueError("File h3_river.csv không có cột river_proximity_fraction")
    return df


def load_h3_grid():
    if not os.path.exists(H3_GRID_GEOJSON):
        raise FileNotFoundError(f"Không tìm thấy file: {H3_GRID_GEOJSON}")
    gdf = gpd.read_file(H3_GRID_GEOJSON)
    gdf["h3_index"] = gdf["h3_index"].astype(str)
    return gdf


def make_discrete_cmap(n_bins=100):
    cmap = plt.cm.Blues
    colors = [cmap(i) for i in np.linspace(0.20, 0.95, n_bins)]
    return ListedColormap(colors), BoundaryNorm(np.linspace(0.0, 1.0, n_bins + 1), n_bins)


def main():
    args = parse_args()
    
    river_df = load_river_csv()
    h3_grid = load_h3_grid()
    h3_grid = h3_grid.merge(river_df[["h3_index", "river_proximity_fraction"]], on="h3_index", how="left")

    cmap, norm = make_discrete_cmap(100)

    fig, ax = plt.subplots(figsize=(12, 10))
    
    h3_grid.plot(
        ax=ax,
        column="river_proximity_fraction",
        cmap=cmap,
        norm=norm,
        linewidth=0.08,
        edgecolor="none",
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax.set_title("H3 grid by river_proximity_fraction (100 bins)")
    ax.axis("off")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("river_proximity_fraction")

    plt.tight_layout()
    
    if args.save:
        os.makedirs(os.path.dirname(args.save), exist_ok=True)
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {args.save}")
    
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
