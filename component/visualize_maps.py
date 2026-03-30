"""
Visualize maps: raw shapefile, clean shapefile, and H3 grid.
All paths are loaded from src/config.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from src.config import (
    SHAPEFILE_RAW,
    SHAPEFILE_CLEAN,
    H3_GRID_GEOJSON,
    DATA_PROCESSED
)


def plot_raw_shapefile(ax=None, show=False):
    """Vẽ shapefile raw (boundary_input.shp)"""
    gdf = gpd.read_file(SHAPEFILE_RAW)
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    gdf.plot(ax=ax, edgecolor='red', facecolor='lightcoral', alpha=0.5, linewidth=1.5)
    ax.set_title("Raw Boundary (boundary_input.shp)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    if show:
        plt.tight_layout()
        plt.show()
    
    return ax


def plot_clean_shapefile(ax=None, show=False):
    """Vẽ shapefile đã clean (boundary_clean.shp)"""
    gdf = gpd.read_file(SHAPEFILE_CLEAN)
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    gdf.plot(ax=ax, edgecolor='blue', facecolor='lightblue', alpha=0.5, linewidth=1.5)
    ax.set_title("Clean Boundary (boundary_clean.shp)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    if show:
        plt.tight_layout()
        plt.show()
    
    return ax


def plot_h3_grid(ax=None, show=False):
    """Vẽ lưới H3 từ GeoJSON"""
    gdf = gpd.read_file(H3_GRID_GEOJSON)
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    gdf.plot(ax=ax, edgecolor='green', facecolor='lightgreen', alpha=0.4, linewidth=0.5)
    ax.set_title(f"H3 Grid ({len(gdf)} cells)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    if show:
        plt.tight_layout()
        plt.show()
    
    return ax


def plot_all_maps(save_path=None):
    """Vẽ tất cả 3 bản đồ cạnh nhau"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 8))
    
    # Plot raw shapefile
    plot_raw_shapefile(ax=axes[0])
    
    # Plot clean shapefile
    plot_clean_shapefile(ax=axes[1])
    
    # Plot H3 grid
    plot_h3_grid(ax=axes[2])
    
    plt.suptitle("Mekong DGGS - Map Visualization", fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    plt.show()


def plot_comparison(save_path=None):
    """Vẽ so sánh raw vs clean vs H3 grid chồng lên nhau"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    
    # Load all data
    gdf_raw = gpd.read_file(SHAPEFILE_RAW)
    gdf_clean = gpd.read_file(SHAPEFILE_CLEAN)
    gdf_h3 = gpd.read_file(H3_GRID_GEOJSON)
    
    # Plot layers
    gdf_raw.plot(ax=ax, edgecolor='red', facecolor='none', linewidth=2, linestyle='--', label='Raw')
    gdf_clean.plot(ax=ax, edgecolor='blue', facecolor='none', linewidth=2, label='Clean')
    gdf_h3.plot(ax=ax, edgecolor='green', facecolor='lightgreen', alpha=0.3, linewidth=0.3, label='H3 Grid')
    
    # Legend
    legend_elements = [
        Patch(facecolor='none', edgecolor='red', linewidth=2, linestyle='--', label='Raw Boundary'),
        Patch(facecolor='none', edgecolor='blue', linewidth=2, label='Clean Boundary'),
        Patch(facecolor='lightgreen', edgecolor='green', alpha=0.5, label=f'H3 Grid ({len(gdf_h3)} cells)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    ax.set_title("Comparison: Raw vs Clean vs H3 Grid", fontsize=14, fontweight='bold')
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    plt.show()


if __name__ == "__main__":
    print("=" * 60)
    print("Mekong DGGS - Map Visualization")
    print("=" * 60)
    print(f"Raw shapefile:   {SHAPEFILE_RAW}")
    print(f"Clean shapefile: {SHAPEFILE_CLEAN}")
    print(f"H3 Grid:         {H3_GRID_GEOJSON}")
    print("=" * 60)
    
    # Tạo thư mục output nếu chưa có
    output_dir = os.path.join(DATA_PROCESSED, "figures")
    os.makedirs(output_dir, exist_ok=True)
    
    # Vẽ tất cả các bản đồ riêng biệt
    print("\n[1/2] Plotting all maps side by side...")
    plot_all_maps(save_path=os.path.join(output_dir, "all_maps.png"))
    
    # Vẽ so sánh chồng lớp
    print("\n[2/2] Plotting comparison overlay...")
    plot_comparison(save_path=os.path.join(output_dir, "comparison.png"))
    
    print("\n✓ Done! Figures saved to:", output_dir)
