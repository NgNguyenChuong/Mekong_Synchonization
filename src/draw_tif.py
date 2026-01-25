import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.plot import show

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN
# ==========================================
# Đường dẫn tới thư mục chứa ảnh Landsat 8 vừa tải
# (Khớp với OUTPUT_DIR ở code trước)
INPUT_DIR = "../data/processed/landsat_salinity_2022_full_year"

# Tên file bạn muốn xem (Nếu để None, code sẽ tự lấy file đầu tiên tìm thấy)
TARGET_FILE = '2022_M09_L89_Salinity.tif'  # <-- Thay đổi tên file ở đây nếu cần
# Ví dụ cụ thể: TARGET_FILE = "2022_M02_L8_NDWI_Salinity.tif"

# ==========================================
# HÀM XỬ LÝ
# ==========================================
def visualize_salinity_map(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Lỗi: Không tìm thấy file {file_path}")
        return

    print(f"✅ Đang đọc file: {os.path.basename(file_path)} ...")

    with rasterio.open(file_path) as src:
        # 1. Đọc dữ liệu (Lưu ý: Band 1 là NDWI, Band 2 là Salinity)
        ndwi = src.read(1)
        salinity = src.read(2)
        
        # Đọc mask (để loại bỏ các điểm NoData/Background đen sì)
        mask = src.read_masks(1)
        
        # 2. Xử lý dữ liệu để hiển thị đẹp hơn
        # Chuyển các giá trị 0 hoặc NoData thành NaN để không vẽ lên biểu đồ
        ndwi = np.where(mask > 0, ndwi, np.nan)
        salinity = np.where(mask > 0, salinity, np.nan)

        # 3. Tính toán thống kê nhanh
        print(f"\n📊 Thống kê dữ liệu:")
        print(f"   - NDWI     : Min={np.nanmin(ndwi):.3f}, Max={np.nanmax(ndwi):.3f}, Mean={np.nanmean(ndwi):.3f}")
        print(f"   - Salinity : Min={np.nanmin(salinity):.3f}, Max={np.nanmax(salinity):.3f}, Mean={np.nanmean(salinity):.3f}")

        # 4. Vẽ biểu đồ
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # --- Bản đồ NDWI ---
        # NDWI thường từ -1 đến 1. Nước > 0. 
        # Dùng colormap 'RdBu' (Đỏ-Xanh): Xanh là nước, Đỏ là đất.
        im1 = ax1.imshow(ndwi, cmap='RdBu', vmin=-0.6, vmax=0.6)
        ax1.set_title("Band 1: Chỉ số Nước (NDWI)")
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Giá trị chỉ số")
        ax1.axis('off') # Tắt trục tọa độ cho đẹp

        # --- Bản đồ Độ mặn (Salinity) ---
        # Dùng colormap 'YlOrRd' (Vàng-Cam-Đỏ) hoặc 'jet'
        # Dùng vmin/vmax theo phân vị 2% - 98% để loại bỏ điểm nhiễu (outlier), giúp ảnh rõ hơn
        vmin, vmax = np.nanpercentile(salinity, [2, 98])
        
        im2 = ax2.imshow(salinity, cmap='YlOrRd', vmin=vmin, vmax=vmax)
        ax2.set_title("Band 2: Độ mặn ước tính (Salinity)")
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Độ mặn (theo công thức)")
        ax2.axis('off')

        plt.suptitle(f"Kết quả phân tích Landsat 8: {os.path.basename(file_path)}", fontsize=16)
        plt.tight_layout()
        plt.show()

# ==========================================
# CHẠY CHƯƠNG TRÌNH
# ==========================================
if __name__ == "__main__":
    # Tự động tìm file nếu chưa chỉ định
    if TARGET_FILE is None:
        if os.path.exists(INPUT_DIR):
            files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.tif')]
            if len(files) > 0:
                TARGET_FILE = files[0] # Lấy file đầu tiên
                full_path = os.path.join(INPUT_DIR, TARGET_FILE)
                visualize_salinity_map(full_path)
            else:
                print(f"⚠️ Thư mục {INPUT_DIR} rỗng. Hãy chạy code tải dữ liệu trước!")
        else:
            print(f"⚠️ Thư mục {INPUT_DIR} chưa được tạo.")
    else:
        # Chạy file cụ thể
        full_path = os.path.join(INPUT_DIR, TARGET_FILE)
        visualize_salinity_map(full_path)