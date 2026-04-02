#!/usr/bin/env python
"""Draw the path from one H3 cell centroid to the nearest river pixel."""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, FancyArrowPatch
from rasterio.plot import plotting_extent
from scipy.spatial import cKDTree


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED, H3_GRID_GEOJSON, SHAPEFILE_CLEAN, SHAPEFILE_RAW  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Draw a path from one H3 cell to the nearest river pixel")
    parser.add_argument("--h3-index", default=None, help="Target H3 index. If omitted, the first cell in the grid is used.")
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


def load_river_raster():
    tif_path = os.path.join(DATA_RAW, "river", "River_DBSCL.tif")
    if not os.path.exists(tif_path):
        raise FileNotFoundError(f"Không tìm thấy file: {tif_path}")

    with rasterio.open(tif_path) as src:
        data = src.read(1)
        extent = plotting_extent(src)
        nodata = src.nodata
        crs = src.crs
        transform = src.transform

    if nodata is not None:
        river_mask = (data == 1) & (data != nodata)
    else:
        river_mask = (data == 1)

    rows, cols = np.where(river_mask)
    if len(rows) == 0:
        raise ValueError("Không tìm thấy pixel sông nào trong raster.")

    with rasterio.open(tif_path) as src:
        xs, ys = rasterio.transform.xy(src.transform, rows, cols)

    river_coords = np.column_stack((xs, ys))
    return tif_path, data, extent, river_mask, river_coords, crs, transform


def pick_target_h3(grid, h3_index):
    if h3_index:
        target = grid[grid["h3_index"] == str(h3_index)]
        if target.empty:
            raise ValueError(f"Không tìm thấy ô H3: {h3_index}")
        return target.iloc[0]
    return grid.iloc[0]


def nearest_river_point(centroid_xy, river_coords):
    tree = cKDTree(river_coords)
    distance, index = tree.query([centroid_xy])
    return river_coords[index[0]], float(distance[0])


def main():
    args = parse_args()

    grid = load_grid()
    boundary = load_boundary()
    tif_path, river_data, extent, river_mask, river_coords, crs, transform = load_river_raster()

    target_row = pick_target_h3(grid, args.h3_index)
    target_geom = target_row.geometry
    centroid = target_geom.centroid
    centroid_xy = (centroid.x, centroid.y)
    nearest_xy, distance_raw = nearest_river_point(centroid_xy, river_coords)

    if crs and crs.is_geographic:
        distance_km = distance_raw * 111.32
    else:
        distance_km = distance_raw / 1000.0

    selected = grid[grid["h3_index"] == target_row["h3_index"]]
    others = grid[grid["h3_index"] != target_row["h3_index"]]

    fig, ax = plt.subplots(figsize=(13, 11))
    ax.set_facecolor("#f7f7f7")

    # Raster river background
    cmap = ListedColormap(["#f8f9fa", "#1d4ed8"])
    ax.imshow(np.ma.masked_invalid(river_data), cmap=cmap, extent=extent, origin="upper", alpha=0.85)

    # Optional boundary overlay
    if boundary is not None:
        boundary.plot(ax=ax, facecolor="none", edgecolor="#444444", linewidth=1.0, alpha=0.8)

    # All H3 cells faint, selected cell emphasized
    if not others.empty:
        others.plot(ax=ax, facecolor="none", edgecolor="#9ca3af", linewidth=0.15, alpha=0.35)
    selected.plot(ax=ax, facecolor="none", edgecolor="#ef4444", linewidth=1, alpha=1.0)

    # Draw the path from centroid to nearest river pixel
    path_arrow = FancyArrowPatch(
        (centroid.x, centroid.y),
        (nearest_xy[0], nearest_xy[1]),
        arrowstyle="->",
        mutation_scale=5,
        linewidth=1,
        linestyle="--",
        color="#111827",
        zorder=6,
    )
    ax.add_patch(path_arrow)

    step_text = (
        "Các bước tính:\n"
        "1) Lấy centroid của ô H3\n"
        "2) Tìm pixel sông gần nhất\n"
        "3) Nối 2 điểm bằng đường thẳng\n"
        "4) Đổi sang km và trả kết quả"
    )
    ax.text(
        0.02,
        0.02,
        step_text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        color="#111827",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#d1d5db", alpha=0.96),
    )

    info_text = (
        f"H3: {target_row['h3_index']}\n"
        f"Nearest river: {distance_km:.2f} km"
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

    ax.set_title("Đường đi từ ô H3 tới sông gần nhất", fontsize=18, fontweight="bold", color="#102542")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    legend_handles = [
        Patch(facecolor="#ef4444", edgecolor="#7f1d1d", label="Selected H3"),
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
