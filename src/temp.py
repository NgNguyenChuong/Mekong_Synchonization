import os
import ee
import geemap
from datetime import datetime

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & EARTH ENGINE
# ==============================================================================

# --- Cấu hình Đường dẫn ---
try:
    from config import DATA_PROCESSED, GEE_PROJECT
    # Bỏ qua CRS cũ từ config nếu bạn muốn ép cứng dùng 4326
except ImportError:
    print("⚠️ Không tìm thấy config.py. Sử dụng cấu hình mặc định.")
    DATA_PROCESSED = "./data/processed" # Hoặc đường dẫn ổ D:/ của bạn
    GEE_PROJECT = None 

# --- [QUAN TRỌNG] THIẾT LẬP CRS MỚI ---
# Sử dụng WGS 84 (Kinh độ/Vĩ độ)
CRS_EXPORT = "EPSG:4326"

# --- Khởi tạo Earth Engine ---
try:
    if GEE_PROJECT:
        ee.Initialize(project=GEE_PROJECT)
    else:
        ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# --- Tham số thời gian & Không gian ---
years = [2021, 2022, 2023]
roi = ee.Geometry.Rectangle([104.5, 8.3, 106.9, 11.3]) # Vùng ĐBSCL

dry_months = [
    {'month': 11, 'year_offset': -1},
    {'month': 12, 'year_offset': -1},
    {'month': 1,  'year_offset': 0},
    {'month': 2,  'year_offset': 0},
    {'month': 3,  'year_offset': 0},
    {'month': 4,  'year_offset': 0}
]

# Thư mục Output
OUTPUT_DIR = os.path.join(DATA_PROCESSED, "landsat_merged_salinity_wgs84")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# 2. CÁC HÀM XỬ LÝ ẢNH (GIỮ NGUYÊN LOGIC)
# ==============================================================================

def preprocess_landsat(image):
    """Xử lý L8 và L9: Scale, Mask mây"""
    qa_mask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
    sat_mask = image.select('QA_RADSAT').eq(0)
    optical_bands = image.select(['SR_B5', 'SR_B7']).multiply(0.0000275).add(-0.2)

    return (image.addBands(optical_bands, None, True)
                 .updateMask(qa_mask)
                 .updateMask(sat_mask)
                 .select(['SR_B5', 'SR_B7']))

def iterative_gap_fill(image):
    """Vá lỗ 2 bước"""
    filled_1 = image.focal_mean(1.5, 'square', 'pixels', 1)
    img_f1 = image.unmask(filled_1)
    filled_2 = img_f1.focal_mean(3, 'square', 'pixels', 1)
    return img_f1.unmask(filled_2)

def calculate_indices(image):
    """Tính NDWI và Độ mặn"""
    ndwi = image.normalizedDifference(['SR_B5', 'SR_B7']).rename('NDWIchen')
    salinity = image.expression(
        '28.013 * exp(-13.39 * NIR)',
        {'NIR': image.select('SR_B5')}
    ).rename('Salinity').toFloat()
    return ndwi.addBands(salinity)

# ==============================================================================
# 3. VÒNG LẶP CHÍNH
# ==============================================================================

print(f"🚀 BẮT ĐẦU XỬ LÝ (EPSG:4326 - WGS84)")
print(f"📂 Output: {os.path.abspath(OUTPUT_DIR)}")

for year in years:
    for month_info in dry_months:
        actual_year = year + month_info['year_offset']
        month = month_info['month']
        
        base_date = ee.Date.fromYMD(actual_year, month, 15)
        start_date = base_date.advance(-20, 'day')
        end_date = base_date.advance(20, 'day')
        
        file_name = f'{actual_year}_M{month:02d}_L89_Salinity_WGS84.tif'
        output_path = os.path.join(OUTPUT_DIR, file_name)

        if os.path.exists(output_path):
            print(f"⏭️  [Skip] Đã có: {file_name}")
            continue
            
        print(f"---------------------------------------------")
        print(f"🔄 Đang xử lý: {month}/{actual_year}")

        try:
            l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterBounds(roi).filterDate(start_date, end_date)
            l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterBounds(roi).filterDate(start_date, end_date)
            
            merged_col = l8.merge(l9).map(preprocess_landsat)
            
            count = merged_col.size().getInfo()
            if count == 0:
                print(f"⚠️  [Warn] Không tìm thấy ảnh. Bỏ qua.")
                continue
            
            # Tính toán
            composite = merged_col.median().clip(roi)
            composite_clean = iterative_gap_fill(composite)
            final_image = calculate_indices(composite_clean)

            # Check nhanh dữ liệu
            stats = final_image.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=roi, scale=5000, bestEffort=True
            ).getInfo()
            
            if stats.get('Salinity') is None:
                print(f"   ❌ [Error] Ảnh rỗng (NoData).")
                continue

            # TẢI VỀ VỚI EPSG:4326
            print(f"   ⬇️  Đang tải xuống (WGS84)...")
            geemap.download_ee_image(
                image=final_image,
                filename=output_path,
                region=roi,
                scale=30,           # Vẫn để 30, GEE tự quy đổi sang độ
                crs=CRS_EXPORT,     # <-- Dùng EPSG:4326
                dtype='float32',
                num_threads=8
            )
            print(f"   ✅ Hoàn tất: {file_name}")

        except Exception as e:
            print(f"   ❌ Lỗi: {e}")

print('=============================================')
print('🎉 HOÀN TẤT!')