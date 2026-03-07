import argparse
import os

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import CRS_WGS84, DATA_PROCESSED, DATA_SPECS, H3_GRID_GEOJSON, SHAPEFILE_CLEAN


def _default_csv_path():
    for key in ("solar", "rain", "temp_avg", "temp_max", "temp_min", "humidity"):
        spec = DATA_SPECS.get(key)
        if spec:
            return os.path.join(DATA_PROCESSED, spec["output_file"])

    if DATA_SPECS:
        first = next(iter(DATA_SPECS.values()))
        return os.path.join(DATA_PROCESSED, first["output_file"])

    raise ValueError("DATA_SPECS is empty. Please configure dataset specs before plotting.")


def _guess_value_column(df):
    excluded = {"h3_index", "date"}
    candidates = [c for c in df.columns if c not in excluded]
    if not candidates:
        raise ValueError(
            "Cannot detect value column. CSV must contain at least one data column besides 'h3_index' and 'date'."
        )
    return candidates[0]


def load_inputs(boundary_path, grid_path, csv_path):
    if not os.path.exists(boundary_path):
        raise FileNotFoundError(f"Boundary file not found: {boundary_path}")
    if not os.path.exists(grid_path):
        raise FileNotFoundError(f"H3 grid file not found: {grid_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    boundary = gpd.read_file(boundary_path).to_crs(CRS_WGS84)
    h3_grid = gpd.read_file(grid_path).to_crs(CRS_WGS84)

    if "h3_index" not in h3_grid.columns:
        raise ValueError("H3 grid must contain 'h3_index' column.")

    df = pd.read_csv(csv_path, dtype={"h3_index": str})
    if "h3_index" not in df.columns:
        raise ValueError("CSV must contain 'h3_index' column.")

    return boundary, h3_grid, df


def build_nodata_index(df, value_col, date_filter=None):
    df = df.copy()
    df[value_col] = df[value_col].replace(-9999.0, np.nan)

    if date_filter:
        if "date" not in df.columns:
            raise ValueError("date_filter was provided but CSV has no 'date' column.")
        df = df[df["date"] == date_filter]

    missing = df[df[value_col].isna()]
    return set(missing["h3_index"].astype(str).unique())


def plot_nodata(boundary, h3_grid, nodata_h3, value_col, date_filter=None, save_path=None, show=True):
    h3_grid = h3_grid.copy()
    h3_grid["h3_index"] = h3_grid["h3_index"].astype(str)

    h3_nodata = h3_grid[h3_grid["h3_index"].isin(nodata_h3)]
    h3_valid = h3_grid[~h3_grid["h3_index"].isin(nodata_h3)]

    total_cells = len(h3_grid)
    num_nodata = len(h3_nodata)
    pct = (num_nodata / total_cells * 100.0) if total_cells else 0.0

    fig, ax = plt.subplots(figsize=(12, 12))

    boundary.plot(
        ax=ax,
        facecolor="#f5f5f5",
        edgecolor="black",
        linewidth=1.0,
        alpha=0.8,
    )

    if not h3_valid.empty:
        h3_valid.plot(
            ax=ax,
            facecolor="none",
            edgecolor="#2E8B57",
            linewidth=0.15,
            alpha=0.4,
        )

    if not h3_nodata.empty:
        h3_nodata.plot(
            ax=ax,
            facecolor="#D32F2F",
            edgecolor="#7F1D1D",
            linewidth=0.4,
            alpha=0.85,
        )

    subtitle = f"metric={value_col}"
    if date_filter:
        subtitle += f" | date={date_filter}"

    ax.set_title(
        f"H3 NoData Check\nTotal={total_cells} | Missing={num_nodata} ({pct:.2f}%) | {subtitle}",
        fontsize=13,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")

    legend_patches = [
        mpatches.Patch(facecolor="#f5f5f5", edgecolor="black", label="Boundary"),
        mpatches.Patch(facecolor="none", edgecolor="#2E8B57", label="Valid cells"),
        mpatches.Patch(facecolor="#D32F2F", edgecolor="#7F1D1D", label="NoData cells"),
    ]
    ax.legend(handles=legend_patches, loc="lower right")

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=180)
        print(f"Saved figure: {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return total_cells, num_nodata


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize NoData cells on H3 grid.")
    parser.add_argument("--boundary", default=SHAPEFILE_CLEAN, help="Path to cleaned boundary shapefile (.shp)")
    parser.add_argument("--grid", default=H3_GRID_GEOJSON, help="Path to H3 grid GeoJSON")
    parser.add_argument("--csv", default=_default_csv_path(), help="Path to H3 dataset CSV")
    parser.add_argument("--value-col", default=None, help="Value column to inspect (auto-detect if omitted)")
    parser.add_argument("--date", default=None, help="Filter one date (YYYY-MM-DD)")
    parser.add_argument(
        "--save",
        default=os.path.join(DATA_PROCESSED, "nodata_check.png"),
        help="Output PNG path. Use empty string to disable saving.",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not open matplotlib window")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Boundary:", args.boundary)
    print("H3 Grid :", args.grid)
    print("CSV     :", args.csv)

    boundary, h3_grid, df = load_inputs(args.boundary, args.grid, args.csv)

    value_col = args.value_col or _guess_value_column(df)
    if value_col not in df.columns:
        raise ValueError(f"value column '{value_col}' not found in CSV.")

    nodata_h3 = build_nodata_index(df, value_col=value_col, date_filter=args.date)

    total_cells, num_nodata = plot_nodata(
        boundary=boundary,
        h3_grid=h3_grid,
        nodata_h3=nodata_h3,
        value_col=value_col,
        date_filter=args.date,
        save_path=(args.save if args.save else None),
        show=not args.no_show,
    )

    print("-" * 40)
    if num_nodata > 0:
        print(f"NoData detected: {num_nodata}/{total_cells} cells")
    else:
        print("No NoData cells detected.")
    print("-" * 40)


if __name__ == "__main__":
    main()
