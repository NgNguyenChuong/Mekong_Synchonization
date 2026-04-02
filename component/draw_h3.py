import argparse
import os
import sys

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Load các đường dẫn từ config
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
from src.config import CRS_WGS84, DATA_PROCESSED, H3_GRID_GEOJSON, SHAPEFILE_CLEAN


def _guess_value_column(df):
    excluded = {"h3_index", "date"}
    candidates = [c for c in df.columns if c not in excluded]
    if not candidates:
        raise ValueError("Cannot detect value column in CSV.")
    return candidates[0]


def load_inputs(boundary_path, grid_path, dyn_csv_path, stat_csv_path):
    print("⏳ Đang tải bản đồ ranh giới và lưới H3...")
    boundary = gpd.read_file(boundary_path).to_crs(CRS_WGS84)
    h3_grid = gpd.read_file(grid_path).to_crs(CRS_WGS84)
    h3_grid["h3_index"] = h3_grid["h3_index"].astype(str)

    # Đọc dữ liệu Động
    print(f"📖 Đang đọc dữ liệu Động: {os.path.basename(dyn_csv_path)}")
    if not os.path.exists(dyn_csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {dyn_csv_path}")
    df_dyn = pd.read_csv(dyn_csv_path, dtype={"h3_index": str})

    # Đọc dữ liệu Tĩnh
    print(f"📖 Đang đọc dữ liệu Tĩnh: {os.path.basename(stat_csv_path)}")
    if not os.path.exists(stat_csv_path):
        raise FileNotFoundError(f"Không tìm thấy file: {stat_csv_path}")
    df_stat = pd.read_csv(stat_csv_path, dtype={"h3_index": str})

    return boundary, h3_grid, df_dyn, df_stat


def build_nodata_index(df, value_col, date_filter=None):
    df = df.copy()
    df[value_col] = df[value_col].replace([-9999.0, "-9999", -9999, None], np.nan)

    if date_filter and "date" in df.columns:
        df = df[df["date"] == date_filter]

    missing = df[df[value_col].isna()]
    return set(missing["h3_index"].astype(str).unique())


def _draw_map(ax, boundary, h3_grid, nodata_h3, title):
    """Hàm vẽ bản đồ con lên một trục (Axis) cụ thể"""
    h3_nodata = h3_grid[h3_grid["h3_index"].isin(nodata_h3)]
    h3_valid = h3_grid[~h3_grid["h3_index"].isin(nodata_h3)]

    total = len(h3_grid)
    missing = len(h3_nodata)
    pct = (missing / total * 100.0) if total else 0.0

    boundary.plot(ax=ax, facecolor="#f5f5f5", edgecolor="black", linewidth=1.0, alpha=0.8)

    if not h3_valid.empty:
        h3_valid.plot(ax=ax, facecolor="none", edgecolor="#2E8B57", linewidth=0.15, alpha=0.4)

    if not h3_nodata.empty:
        h3_nodata.plot(ax=ax, facecolor="#D32F2F", edgecolor="#7F1D1D", linewidth=0.4, alpha=0.85)

    ax.set_title(f"{title}\nTotal={total} | Missing={missing} ({pct:.2f}%)", fontsize=12)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def plot_dual_nodata(boundary, h3_grid, nodata_dyn, col_dyn, date_dyn, nodata_stat, col_stat, save_path=None, show=True):
    # Tạo 1 Figure với 2 Subplots (1 hàng, 2 cột)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    fig.suptitle("H3 Grid Data Completeness Check", fontsize=18, fontweight="bold")

    # Vẽ bản đồ ĐỘNG (Trái)
    title_dyn = f"[DYNAMIC] Metric: {col_dyn}"
    if date_dyn:
        title_dyn += f" | Date: {date_dyn}"
    _draw_map(ax1, boundary, h3_grid, nodata_dyn, title_dyn)

    # Vẽ bản đồ TĨNH (Phải)
    title_stat = f"[STATIC] Metric: {col_stat}"
    _draw_map(ax2, boundary, h3_grid, nodata_stat, title_stat)

    # Thêm Legend chung ở dưới cùng
    legend_patches = [
        mpatches.Patch(facecolor="#f5f5f5", edgecolor="black", label="Boundary"),
        mpatches.Patch(facecolor="none", edgecolor="#2E8B57", label="Valid Data"),
        mpatches.Patch(facecolor="#D32F2F", edgecolor="#7F1D1D", label="NoData (Missing)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3, fontsize=12, bbox_to_anchor=(0.5, 0.02))

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"✅ Đã lưu ảnh kiểm tra tại: {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize NoData cells for both Dynamic and Static H3 datasets.")
    parser.add_argument("--date", default=None, help="Lọc theo ngày cho biến động (VD: 2021-01-01)")
    parser.add_argument("--val-dyn", default=None, help="Tên cột ĐỘNG muốn kiểm tra (Mặc định: Tự tìm)")
    parser.add_argument("--val-stat", default=None, help="Tên cột TĨNH muốn kiểm tra (Mặc định: Tự tìm)")
    parser.add_argument("--save", default=os.path.join(DATA_PROCESSED, "dual_nodata_check.png"))
    parser.add_argument("--no-show", action="store_true", help="Chỉ lưu ảnh, không mở cửa sổ hiện lên")
    return parser.parse_args()


def main():
    args = parse_args()

    # Đường dẫn mặc định
    dyn_csv_path = os.path.join(DATA_PROCESSED, "FINAL_MERGED_DATASET.csv")
    stat_csv_path = os.path.join(DATA_PROCESSED, "DIM_H3_STATIC.csv")

    try:
        boundary, h3_grid, df_dyn, df_stat = load_inputs(SHAPEFILE_CLEAN, H3_GRID_GEOJSON, dyn_csv_path, stat_csv_path)
    except Exception as e:
        print(f"❌ Lỗi tải dữ liệu: {e}")
        return

    # Tự động lấy cột nếu người dùng không truyền vào
    col_dyn = args.val_dyn or _guess_value_column(df_dyn)
    col_stat = args.val_stat or _guess_value_column(df_stat)

    print(f"🔍 Kiểm tra Động: cột '{col_dyn}' (Ngày: {args.date if args.date else 'Tất cả'})")
    print(f"🔍 Kiểm tra Tĩnh: cột '{col_stat}'")

    # Xác định các ô bị NoData
    nodata_dyn = build_nodata_index(df_dyn, value_col=col_dyn, date_filter=args.date)
    nodata_stat = build_nodata_index(df_stat, value_col=col_stat, date_filter=None) # Static không có ngày

    # Vẽ 2 bản đồ cùng lúc
    plot_dual_nodata(
        boundary=boundary,
        h3_grid=h3_grid,
        nodata_dyn=nodata_dyn,
        col_dyn=col_dyn,
        date_dyn=args.date,
        nodata_stat=nodata_stat,
        col_stat=col_stat,
        save_path=args.save,
        show=not args.no_show
    )

if __name__ == "__main__":
    main()