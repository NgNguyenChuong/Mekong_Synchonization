import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from config import (
    CRS_WGS84,
    SHAPEFILE_CLEAN,
    H3_GRID_GEOJSON,
    DATA_PROCESSED
)

def draw_mekong_h3_map(data_csv_name="h3_solar_daily_filled.csv", column_to_plot="solar", date_filter=None):
    # ============================================================
    # 1. CẤU HÌNH ĐƯỜNG DẪN
    # ============================================================
    path_csv = os.path.join(DATA_PROCESSED, data_csv_name)
    
    print(f"📂 Đang tải Shapefile: {SHAPEFILE_CLEAN}")
    print(f"📂 Đang tải H3 Grid: {H3_GRID_GEOJSON}")
    print(f"📂 Đang tải Dữ liệu: {path_csv}")

    # ============================================================
    # 2. LOAD DỮ LIỆU
    # ============================================================
    # Đọc Boundary & H3 Grid
    boundary = gpd.read_file(SHAPEFILE_CLEAN).to_crs(CRS_WGS84)
    h3_grid = gpd.read_file(H3_GRID_GEOJSON).to_crs(CRS_WGS84)

    # Đọc dữ liệu CSV
    if os.path.exists(path_csv):
        df = pd.read_csv(path_csv)
        
        # Lọc theo ngày (nếu cần) để tránh duplicate h3_index khi vẽ
        if date_filter:
            df = df[df['date'] == date_filter]
        else:
            # Nếu không lọc ngày, lấy trung bình theo h3_index để vẽ tổng quan
            print("⚠️ Không chọn ngày cụ thể, tính trung bình giá trị theo từng ô H3...")
            df = df.groupby("h3_index")[column_to_plot].mean().reset_index()

        # Merge dữ liệu vào GeoDataFrame của H3
        # h3_grid (geometry) LEFT JOIN df (data) ON h3_index
        h3_mapped = h3_grid.merge(df, on="h3_index", how="left")
    else:
        print(f"⚠️ Không tìm thấy file {path_csv}, chỉ vẽ lưới H3 rỗng.")
        h3_mapped = h3_grid
        h3_mapped[column_to_plot] = 0 # Dummy data

    # ============================================================
    # 3. VẼ BẢN ĐỒ
    # ============================================================
    fig, ax = plt.subplots(figsize=(12, 12))

    # A. Vẽ Ranh giới (Boundary) làm nền
    boundary.plot(
        ax=ax,
        facecolor="none",
        edgecolor="black",
        linewidth=1.5,
        zorder=3,
        label="Ranh giới ĐBSCL"
    )

    # B. Vẽ các ô H3
    if column_to_plot in h3_mapped.columns:
        h3_mapped.plot(
            column=column_to_plot,
            ax=ax,
            cmap="Spectral_r", # Màu: Đỏ (nóng) -> Xanh (lạnh). Dùng 'Blues', 'YlOrRd' tùy thích
            legend=True,
            legend_kwds={'label': f"Giá trị: {column_to_plot}", 'orientation': "horizontal"},
            alpha=0.8,
            edgecolor="grey",
            linewidth=0.1,
            zorder=2
        )
    else:
        # Nếu không có dữ liệu, vẽ lưới rỗng
        h3_mapped.plot(
            ax=ax,
            facecolor="none",
            edgecolor="orange",
            linewidth=0.5,
            zorder=2
        )

    # ============================================================
    # 4. TRANG TRÍ
    # ============================================================
    ax.set_title(f"Bản đồ H3 Đồng bằng sông Cửu Long\nDữ liệu: {column_to_plot}", fontsize=15)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Ví dụ: Vẽ dữ liệu Solar (Bức xạ)
    # Bạn có thể thay đổi tên file CSV và cột dữ liệu ở đây
    # Các cột có sẵn trong config: 'solar', 'rain_mm', 'temp_c', 'rh_percent'
    draw_mekong_h3_map(
        data_csv_name="h3_solar_daily_filled.csv", 
        column_to_plot="solar",
        date_filter="2020-01-01" # Thay đổi ngày này nếu muốn xem ngày cụ thể
    )