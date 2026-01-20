import geopandas as gpd
import os

# --- CẤU HÌNH ---
INPUT_SHP = r"D:\hackathon\Mekong_DGGS\data\raw\DBSCL_Boundary.shp"
OUTPUT_SHP = r"D:\hackathon\Mekong_DGGS\data\raw\DBSCL_Boundary_Clean.shp"

# Ngưỡng diện tích để giữ lại (km2)
# Phú Quốc ~574km2. Nếu bạn muốn bỏ Phú Quốc, hãy đặt threshold > 600
# Các cù lao lớn ở Bến Tre/Trà Vinh đều > 500km2 nên an toàn.
MIN_AREA_KM2 = 600 

def clean_islands():
    print("🧹 Đang làm sạch các đảo nhỏ...")
    
    # 1. Đọc Shapefile
    gdf = gpd.read_file(INPUT_SHP)
    print(f"Số lượng feature gốc: {len(gdf)}")

    # 2. Chuyển sang hệ mét (VN-2000 hoặc UTM 48N) để tính diện tích chính xác
    # EPSG:32648 là UTM Zone 48N
    gdf_metric = gdf.to_crs("EPSG:32648")

    # 3. 'Explode': Tách các tỉnh (MultiPolygon) thành các mảnh đất riêng lẻ (Polygon)
    # Ví dụ: Tỉnh Kiên Giang sẽ tách thành: Đất liền, Đảo Phú Quốc, Đảo Nam Du...
    gdf_exploded = gdf_metric.explode(index_parts=True).reset_index(drop=True)
    
    # 4. Tính diện tích (km2)
    gdf_exploded['area_km2'] = gdf_exploded.geometry.area / 1e6
    
    # 5. Lọc: Chỉ giữ lại các mảnh đất lớn hơn ngưỡng
    gdf_clean = gdf_exploded[gdf_exploded['area_km2'] > MIN_AREA_KM2].copy()
    
    # 6. Gộp lại (Dissolve) - Tùy chọn
    # Nếu bạn muốn gộp tất cả thành 1 hình lớn duy nhất để tạo Grid dễ hơn
    gdf_final = gdf_clean.dissolve()
    
    # 7. Chuyển ngược về Lat/Lon (EPSG:4326) để lưu hoặc dùng tiếp
    gdf_final = gdf_final.to_crs("EPSG:4326")

    # Lưu file
    gdf_final.to_file(OUTPUT_SHP)
    
    print(f"✅ Đã loại bỏ các đảo < {MIN_AREA_KM2} km2.")
    print(f"💾 File sạch lưu tại: {OUTPUT_SHP}")
    
    # In ra danh sách các mảnh được giữ lại để kiểm tra
    print("\nCác vùng đất được giữ lại:")
    print(gdf_clean[['ADM1_NAME', 'area_km2']].sort_values('area_km2', ascending=False).head(10))

if __name__ == "__main__":
    clean_islands()