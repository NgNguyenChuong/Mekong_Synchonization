#!/usr/bin/env python
"""Show H3 landcover as dominant class from h3_landcover.csv."""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import ListedColormap


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_PROCESSED, H3_GRID_GEOJSON  # noqa: E402


CLASS_ORDER = [
    "Trees",
    "Shrubland",
    "Grassland",
    "Cropland",
    "Built_up",
    "Bareland",
    "Water",
    "Wetland",
    "Mangroves",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Show H3 grid by dominant landcover class")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "landcover_h3.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def load_landcover_csv():
    csv_path = os.path.join(DATA_PROCESSED, "h3_landcover.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")

    df = pd.read_csv(csv_path, dtype={"h3_index": str})
    return df


def load_h3_grid():
    if not os.path.exists(H3_GRID_GEOJSON):
        raise FileNotFoundError(f"Không tìm thấy file: {H3_GRID_GEOJSON}")

    gdf = gpd.read_file(H3_GRID_GEOJSON)
    gdf["h3_index"] = gdf["h3_index"].astype(str)
    return gdf


def get_dominant_class(row):
    class_cols = [c for c in row.index if c.startswith("landcover_")]
    if not class_cols:
        return "Unknown"

    best_col = None
    best_val = -1.0
    for col in class_cols:
        val = row[col]
        if pd.notna(val) and val > best_val:
            best_val = val
            best_col = col

    if best_col is None:
        return "Unknown"

    return best_col.replace("landcover_", "")


def main():
    args = parse_args()

    landcover_df = load_landcover_csv()
    h3_grid = load_h3_grid()
    merged = h3_grid.merge(landcover_df, on="h3_index", how="left")

    class_cols = [c for c in merged.columns if c.startswith("landcover_")]
    if not class_cols:
        raise ValueError("Không tìm thấy cột landcover_* trong h3_landcover.csv")

    merged["dominant_class"] = merged.apply(get_dominant_class, axis=1)

    classes_in_data = [c for c in CLASS_ORDER if c in set(merged["dominant_class"].dropna())]
    extra_classes = sorted([c for c in merged["dominant_class"].dropna().unique() if c not in classes_in_data])
    plot_classes = classes_in_data + extra_classes

    palette = [
        "#1b9e77",
        "#66a61e",
        "#a6d854",
        "#ffd92f",
        "#e6ab02",
        "#d95f02",
        "#1f78b4",
        "#6a3d9a",
        "#b15928",
        "#8dd3c7",
        "#bebada",
        "#fb8072",
    ]
    cmap = ListedColormap(palette[: max(1, len(plot_classes))])

    class_to_code = {cls: idx for idx, cls in enumerate(plot_classes)}
    merged["class_code"] = merged["dominant_class"].map(class_to_code)

    fig, ax = plt.subplots(figsize=(12, 10))
    merged.plot(
        ax=ax,
        column="class_code",
        cmap=cmap,
        linewidth=0.08,
        edgecolor="none",
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    ax.set_title("H3 grid by dominant landcover class")
    ax.axis("off")

    handles = []
    for cls, code in class_to_code.items():
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="s",
                color="w",
                markerfacecolor=cmap(code),
                markersize=10,
                label=cls,
            )
        )

    if handles:
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(1.02, 0), frameon=False)

    plt.tight_layout()

    if args.save:
        os.makedirs(os.path.dirname(args.save), exist_ok=True)
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {args.save}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
