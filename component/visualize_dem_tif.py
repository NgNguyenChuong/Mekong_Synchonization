#!/usr/bin/env python
"""Show DEM_DBSCL.tif raster."""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import plotting_extent


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.config import DATA_RAW, DATA_PROCESSED  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Show DEM_DBSCL.tif")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "figures", "dem_raster.png"), help="Output image path")
    parser.add_argument("--no-show", action="store_true", help="Save only, do not display")
    return parser.parse_args()


def main():
    args = parse_args()
    tif_path = os.path.join(DATA_RAW, "dem", "DEM_DBSCL.tif")

    if not os.path.exists(tif_path):
        raise FileNotFoundError(f"Không tìm thấy file: {tif_path}")

    with rasterio.open(tif_path) as src:
        data = src.read(1)
        extent = plotting_extent(src)

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(np.ma.masked_invalid(data), cmap="terrain", extent=extent, origin="upper")
    ax.set_title("DEM_DBSCL.tif")
    ax.axis("off")

    plt.tight_layout()
    
    if args.save:
        os.makedirs(os.path.dirname(args.save), exist_ok=True)
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"✅ Đã lưu ảnh: {args.save}")
    
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
