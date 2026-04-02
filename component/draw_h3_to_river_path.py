#!/usr/bin/env python
"""Draw the path from one H3 cell centroid to the nearest H3 cell with high water fraction."""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, FancyArrowPatch
from scipy.spatial import cKDTree


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED, H3_GRID_GEOJSON, SHAPEFILE_CLEAN, SHAPEFILE_RAW  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Draw a path from one H3 cell to the nearest high-water H3 cell")
    parser.add_argument("--h3-index", default=None, help="Target H3 index. If omitted, the first cell in the grid is used.")
    parser.add_argument("--csv", default=os.path.join(DATA_PROCESSED, "h3_river.csv"), help="Path to H3 river CSV output")
    parser.add_argument("--threshold", type=float, default=0.4, help="Water fraction threshold for water H3 cells (default: 0.40)")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "h3_to_river_path.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def load_boundary():
    boundary_path = SHAPEFILE_CLEAN if os.path.exists(SHAPEFILE_CLEAN) else SHAPEFILE_RAW
    if not os.path.exists(boundary_path):
        return None
    boundary = gpd.read_file(boundary_path)
    if boundary.crs is None:
        boundary = boundary.set_crs("EPSG:4326")
    else:
        boundary = boundary.to_crs("EPSG:4326")
    return boundary


def load_grid():
    if not os.path.exists(H3_GRID_GEOJSON):
        raise FileNotFoundError(f"Không tìm thấy file: {H3_GRID_GEOJSON}")
    gdf = gpd.read_file(H3_GRID_GEOJSON).to_crs("EPSG:4326")
    gdf["h3_index"] = gdf["h3_index"].astype(str)
    return gdf


def load_river_h3_csv(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")

    df = np.genfromtxt(csv_path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    if df.size == 0:
        raise ValueError(f"File CSV rỗng: {csv_path}")

    cols = set(df.dtype.names or [])
    required = {"h3_index", "river_proximity_fraction"}
    if not required.issubset(cols):
        raise ValueError(f"CSV thiếu cột bắt buộc: {sorted(required - cols)}")

    if df.shape == ():
        h3_values = np.array([str(df["h3_index"])])
        frac_values = np.array([float(df["river_proximity_fraction"])])
    else:
        h3_values = np.array([str(v) for v in df["h3_index"]])
        frac_values = df["river_proximity_fraction"].astype(float)

    return h3_values, frac_values


def pick_target_h3(grid, h3_index):
    if h3_index:
        target = grid[grid["h3_index"] == str(h3_index)]
        if target.empty:
            raise ValueError(f"Không tìm thấy ô H3: {h3_index}")
        return target.iloc[0]
    return grid.iloc[0]


def nearest_water_h3(target_point, water_points):
    tree = cKDTree(water_points)
    distance, index = tree.query([target_point], k=1)
    return int(index[0]), float(distance[0])


def main():
    args = parse_args()

    grid = load_grid()
    boundary = load_boundary()
    csv_h3, csv_fraction = load_river_h3_csv(args.csv)

    river_df = pd.DataFrame(
        {"h3_index": csv_h3, "river_proximity_fraction": csv_fraction}
    )
    merged = grid.merge(river_df[["h3_index", "river_proximity_fraction"]], on="h3_index", how="left")
    merged["river_proximity_fraction"] = merged["river_proximity_fraction"].fillna(0.0)

    target_row = pick_target_h3(merged, args.h3_index)
    target_geom = target_row.geometry
    target_id = target_row["h3_index"]

    water_mask = merged["river_proximity_fraction"] > args.threshold
    water_cells = merged[water_mask].copy()
    if water_cells.empty:
        raise ValueError(f"Không có ô H3 nào có tỷ lệ nước > {args.threshold:.0%}")

    merged_metric = merged.to_crs(epsg=3857)
    water_metric = merged_metric[merged_metric["h3_index"].isin(water_cells["h3_index"])].copy()
    target_metric = merged_metric[merged_metric["h3_index"] == target_id]

    target_centroid_metric = target_metric.geometry.iloc[0].centroid
    water_centroids_metric = water_metric.geometry.centroid
    water_points_metric = np.column_stack((water_centroids_metric.x, water_centroids_metric.y))

    nearest_idx, distance_m = nearest_water_h3(
        (target_centroid_metric.x, target_centroid_metric.y),
        water_points_metric,
    )
    nearest_h3_id = water_metric.iloc[nearest_idx]["h3_index"]
    distance_km = distance_m / 1000.0

    selected = merged[merged["h3_index"] == target_id]
    water_all = merged[water_mask].copy()
    water_highlight = merged[merged["h3_index"] == nearest_h3_id]
    others = merged[(~water_mask) & (~merged["h3_index"].isin([target_id, nearest_h3_id]))]

    target_centroid = selected.geometry.iloc[0].centroid
    nearest_centroid = water_highlight.geometry.iloc[0].centroid

    fig, ax = plt.subplots(figsize=(13, 11))
    ax.set_facecolor("#f7f7f7")

    # Optional boundary overlay
    if boundary is not None:
        boundary.plot(ax=ax, facecolor="none", edgecolor="#444444", linewidth=1.0, alpha=0.8)

    # All non-water cells faint
    if not others.empty:
        others.plot(ax=ax, facecolor="none", edgecolor="#9ca3af", linewidth=0.15, alpha=0.35)

    # Draw all high-water cells
    if not water_all.empty:
        water_all.plot(ax=ax, facecolor="#93c5fd", edgecolor="#60a5fa", linewidth=0.3, alpha=0.45)

    # Selected and nearest-water cells emphasized
    selected.plot(ax=ax, facecolor="none", edgecolor="#ef4444", linewidth=1, alpha=1.0)
    water_highlight.plot(ax=ax, facecolor="none", edgecolor="#1d4ed8", linewidth=1, alpha=1.0)

    # Draw the path from centroid to nearest high-water H3 centroid
    path_arrow = FancyArrowPatch(
        (target_centroid.x, target_centroid.y),
        (nearest_centroid.x, nearest_centroid.y),
        arrowstyle="->",
        mutation_scale=5,
        linewidth=1,
        linestyle="--",
        color="#111827",
        zorder=6,
    )
    ax.add_patch(path_arrow)

    info_text = (
        f"H3 nguồn: {target_id}\n"
        f"H3 nước gần nhất: {nearest_h3_id}\n"
        f"Ngưỡng nước: > {args.threshold:.0%}\n"
        f"Số ô nước: {len(water_all)}\n"
        f"Khoảng cách: {distance_km:.2f} km"
    )
    ax.text(
        0.02,
        0.18,
        info_text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color="#111827",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#d1d5db", alpha=0.96),
    )

    ax.set_title("Đường đi từ ô H3 tới ô H3 có tỷ lệ nước cao", fontsize=18, fontweight="bold", color="#102542")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    legend_handles = [
        Patch(facecolor="#93c5fd", edgecolor="#1d4ed8", label="All water H3 (> threshold)"),
        Patch(facecolor="#ef4444", edgecolor="#7f1d1d", label="Selected H3"),
        Patch(facecolor="#1d4ed8", edgecolor="#1e3a8a", label="Nearest water H3 (> threshold)"),
    ]
    ax.legend(handles=legend_handles, loc="lower left", frameon=True)

    plt.tight_layout()

    if args.save:
        os.makedirs(os.path.dirname(args.save), exist_ok=True)
        plt.savefig(args.save, dpi=220, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {args.save}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
