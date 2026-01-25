# import os
# import ee
# import geemap
# from datetime import datetime

# # ==========================================
# # IMPORT TỪ CONFIG CỦA DỰ ÁN
# # ==========================================
# # Giả sử file này nằm trong folder src/, cùng cấp với config.py
# try:
#     from config import (
#         DATA_PROCESSED, # Đường dẫn output
#         CRS_METRIC,     # EPSG:32648
#         GEE_PROJECT     # Project ID
#     )
# except ImportError:
#     # Fallback nếu chạy không đúng vị trí
#     print("⚠️ Không tìm thấy config.py, sử dụng cấu hình mặc định.")
#     DATA_PROCESSED = "./data/processed"
#     CRS_METRIC = "EPSG:32648"
#     GEE_PROJECT = None

# # ==========================================
# # KHỞI TẠO EARTH ENGINE
# # ==========================================
# try:
#     if GEE_PROJECT:
#         ee.Initialize(project='geemap-mekong-483717')
#     else:
#         ee.Initialize()
# except Exception as e:
#     ee.Authenticate()
#     ee.Initialize()

# # ==========================================
# # CẤU HÌNH XỬ LÝ
# # ==========================================
# years = [2021, 2022, 2023]

# # Khu vực: Hình chữ nhật bao quanh ĐBSCL
# # Lưu ý: Nếu muốn dùng Shapefile chính xác từ config, cần dùng geemap.shp_to_ee(SHAPEFILE_CLEAN)
# # Nhưng để nhanh và tránh lỗi upload, ta dùng Rectangle như cũ.
# table = ee.Geometry.Rectangle([104.5, 8.3, 106.9, 11.3])


# dry_months = [
#     {'month': 11, 'year_offset': -1},
#     {'month': 12, 'year_offset': -1},
#     {'month': 1, 'year_offset': 0},
#     {'month': 2, 'year_offset': 0},
#     {'month': 3, 'year_offset': 0},
#     {'month': 4, 'year_offset': 0}
# ]

# # Tạo thư mục con để chứa ảnh vệ tinh
# OUTPUT_DIR = os.path.join(DATA_PROCESSED, "landsat_salinity")
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # ==========================================
# # CÁC HÀM XỬ LÝ (GIỮ NGUYÊN LOGIC CŨ)
# # ==========================================

# def mask_landsat_sr(image):
#     """Lọc mây cho Landsat 8/9"""
#     qa_mask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
#     saturation_mask = image.select('QA_RADSAT').eq(0)
#     optical_bands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
#     return (image.addBands(optical_bands, None, True)
#                  .updateMask(qa_mask)
#                  .updateMask(saturation_mask))

# def smart_gap_fill(image):
#     """Vá lỗ hổng dữ liệu bằng pixel lân cận"""
#     filled = image.focal_mean(2, 'square', 'pixels', 2)
#     return image.unmask(filled)

# # ==========================================
# # MAIN LOOP
# # ==========================================

# print(f"🚀 BẮT ĐẦU QUÁ TRÌNH TẢI DỮ LIỆU")
# print(f"📂 Thư mục lưu: {os.path.abspath(OUTPUT_DIR)}")
# print(f"🌐 CRS Output: {CRS_METRIC}")

# for year in years:
#     for month_info in dry_months:
#         # 1. Thiết lập thời gian
#         actual_year = year + month_info['year_offset']
#         month = month_info['month']
        
#         # Sliding window 5 ngày
#         base_date = ee.Date.fromYMD(actual_year, month, 1)
#         start_date = base_date.advance(-5, 'day')
#         end_date = base_date.advance(1, 'month').advance(5, 'day')
        
#         file_name = f'{actual_year}_M{month:02d}_L89_NDWI_Salinity.tif'
#         output_path = os.path.join(OUTPUT_DIR, file_name)
        
#         # 2. Kiểm tra nếu file đã tồn tại thì bỏ qua (Resume capability)
#         if os.path.exists(output_path):
#             print(f"⏭️  [Skip] Đã tồn tại: {file_name}")
#             continue

#         print(f"---------------------------------------------")
#         print(f"🔄 Đang xử lý: {file_name}")
        
#         # 3. Lấy dữ liệu (L8 + L9)
#         l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
#         l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        
#         collection = (l8.merge(l9)
#                        .filterDate(start_date, end_date)
#                        .filterBounds(table)
#                        .map(mask_landsat_sr))
        
#         count = collection.size().getInfo()
#         if count == 0:
#             print(f"⚠️  [Warn] Không tìm thấy ảnh nào trong tháng này -> Bỏ qua.")
#             continue
            
#         print(f"   ✓ Tìm thấy {count} cảnh ảnh.")

#         # 4. Tính toán
#         composite = collection.median().clip(table)
#         composite_filled = smart_gap_fill(composite)
        
#         ndwi = composite_filled.normalizedDifference(['SR_B5', 'SR_B7']).rename('NDWIchen')
#         salinity = composite_filled.expression(
#             '28.013 * exp(-13.39 * NIR)',
#             {'NIR': composite_filled.select('SR_B5')}
#         ).rename('Salinity').toFloat()
        
#         final_image = ndwi.addBands(salinity)
        
#         # 5. TẢI VỀ LOCAL (Thay thế Export to Drive)
#         print(f"   ⬇️  Đang tải về máy (có thể mất vài phút)...")
        
#         try:
#             # Sử dụng geemap.download_ee_image để tự động chia nhỏ ảnh (tiling)
#             # giúp tránh lỗi giới hạn kích thước của GEE khi tải vùng lớn.
#             geemap.download_ee_image(
#                 image=final_image,
#                 filename=output_path,
#                 region=table,
#                 scale=30,
#                 crs=CRS_METRIC,
#                 dtype='float32',
#                 num_threads=4 # Tải đa luồng cho nhanh
#             )
#             print(f"   ✅ [Hoàn tất] Đã lưu tại: {output_path}")
            
#         except Exception as e:
#             print(f"   ❌ [Lỗi] Không thể tải file này: {e}")

# print('=============================================')
# print('🎉 HOÀN TẤT TOÀN BỘ!')



import os
import ee
import geemap
from datetime import datetime

# ==========================================
# 1. CẤU HÌNH & KHỞI TẠO
# ==========================================
try:
    from config import (
        DATA_PROCESSED, 
        CRS_WGS84,     
        GEE_PROJECT     
    )
except ImportError:
    print("⚠️ Không tìm thấy config.py, sử dụng cấu hình mặc định.")
    DATA_PROCESSED = "./data/processed"
    CRS_WGS84 = "EPSG:4326"
    GEE_PROJECT = None

try:
    if GEE_PROJECT:
        ee.Initialize(project='peaceful-elf-485317-h8')
    else:
        ee.Initialize()
except Exception as e:
    ee.Authenticate()
    ee.Initialize()

# ==========================================
# 2. CẤU HÌNH THỜI GIAN (CHỈ 2022)
# ==========================================
target_year = 2022

# Tạo danh sách 12 tháng của năm 2022
# Range(1, 13) sẽ chạy từ 1 đến 12
months = list(range(1, 13)) 

# Khu vực: Hình chữ nhật bao quanh ĐBSCL
table = ee.Geometry.Rectangle([104.5, 8.3, 106.9, 11.3])

# Thư mục output
OUTPUT_DIR = os.path.join(DATA_PROCESSED, f"landsat_salinity_{target_year}_full_year")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# 3. CÁC HÀM XỬ LÝ
# ==========================================

def mask_landsat_sr(image):
    """Lọc mây cho Landsat 8/9"""
    qa_mask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
    saturation_mask = image.select('QA_RADSAT').eq(0)
    optical_bands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
    return (image.addBands(optical_bands, None, True)
                 .updateMask(qa_mask)
                 .updateMask(saturation_mask))

def smart_gap_fill(image):
    """Vá lỗ hổng dữ liệu bằng pixel lân cận"""
    filled = image.focal_mean(2, 'square', 'pixels', 2)
    return image.unmask(filled)

# ==========================================
# 4. MAIN LOOP (CHẠY 12 THÁNG CỦA 2022)
# ==========================================

print(f"🚀 BẮT ĐẦU XỬ LÝ DỮ LIỆU NĂM {target_year}")
print(f"📂 Thư mục lưu: {os.path.abspath(OUTPUT_DIR)}")

for month in months:
    # 1. Thiết lập thời gian (Ngày 1 đầu tháng -> Ngày cuối tháng)
    start_date = ee.Date.fromYMD(target_year, month, 1)
    end_date = start_date.advance(1, 'month')
    
    file_name = f'{target_year}_M{month:02d}_L89_Salinity.tif'
    output_path = os.path.join(OUTPUT_DIR, file_name)
    
    # 2. Kiểm tra tồn tại (Resume capability)
    if os.path.exists(output_path):
        print(f"⏭️  [Skip] Đã tồn tại: {file_name}")
        continue

    print(f"---------------------------------------------")
    print(f"🔄 Đang xử lý tháng {month}/{target_year}...")
    
    # 3. Lấy dữ liệu (L8 + L9)
    l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    
    collection = (l8.merge(l9)
                    .filterDate(start_date, end_date)
                    .filterBounds(table)
                    .map(mask_landsat_sr))
    
    count = collection.size().getInfo()
    if count == 0:
        print(f"⚠️  [Warn] Tháng {month} không có ảnh nào -> Bỏ qua.")
        continue
        
    print(f"   ✓ Tìm thấy {count} cảnh ảnh.")

    # 4. Tính toán
    # Lấy trung vị (Median) của cả tháng
    composite = collection.median().clip(table)
    composite_filled = smart_gap_fill(composite)
    
    # Tính chỉ số
    ndwi = composite_filled.normalizedDifference(['SR_B5', 'SR_B7']).rename('NDWIchen')
    
    # Công thức độ mặn (dùng Band 5 - NIR)
    salinity = composite_filled.expression(
        '28.013 * exp(-13.39 * NIR)',
        {'NIR': composite_filled.select('SR_B5')}
    ).rename('Salinity').toFloat()
    
    final_image = ndwi.addBands(salinity)
    
    # 5. Tải về
    print(f"   ⬇️  Đang tải về máy...")
    
    try:
        geemap.download_ee_image(
            image=final_image,
            filename=output_path,
            region=table,
            scale=30,
            crs=CRS_WGS84,
            dtype='float32',
            num_threads=4
        )
        print(f"   ✅ [Hoàn tất] {file_name}")
        
    except Exception as e:
        print(f"   ❌ [Lỗi] {e}")

print('=============================================')
print('🎉 HOÀN TẤT NĂM 2022!')