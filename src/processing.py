import os
import pandas as pd
import numpy as np
import h3
import rasterio
import geopandas as gpd
from rasterstats import zonal_stats
from scipy.spatial import cKDTree
from datetime import datetime, timedelta
from utils_h3 import index_files, sample_multiband_robust
from config import FILL_CONFIG, DATA_PROCESSED, DATA_RAW,DATA_SPECS, STATIC_SPECS

# ---------------------------------------------------------
# CORE LOGIC: EXTRACT
# ---------------------------------------------------------
def extract_generic(spec_name, spec_config, h3_data, raw_root_dir):
    h3_ids, point_groups, h3_geoms = h3_data
    input_dir = os.path.join(raw_root_dir, spec_config["folder"])
    col_name = spec_config["col_name"]
    
    file_map = index_files(input_dir)
    if not file_map:
        return pd.DataFrame()

    records = []
    sorted_items = sorted(file_map.items())
    
    # print(f"   ⏳ Extracting {spec_name}...") 
    
    for (year, month), tif_path in sorted_items:
        # Lấy mẫu dữ liệu (Robust sampling)
        vals, _ = sample_multiband_robust(tif_path, point_groups, h3_geoms, n_random=15)
        num_days = len(vals[0]) if vals and vals[0] else 0
        
        for d in range(num_days):
            current_date = datetime(year, month, 1) + timedelta(days=d)
            date_str = current_date.strftime("%Y-%m-%d")
            
            for i, h3_id in enumerate(h3_ids):
                records.append({
                    "h3_index": h3_id,
                    "date": date_str,
                    col_name: vals[i][d]
                })
                
    return pd.DataFrame(records)

# ---------------------------------------------------------
# CORE LOGIC: SPATIAL FILL (K-RING)
# ---------------------------------------------------------
def fill_spatial_generic(df, col_name):
    if df.empty: return df
    
    # Xử lý giá trị rác -9999 thành NaN
    df[col_name] = df[col_name].replace(-9999.0, np.nan)
    
    # Nếu không còn thiếu thì trả về luôn
    if not df[col_name].isna().any():
        return df

    h3_ids = df["h3_index"].unique()
    dates = df["date"].unique()
    max_k = FILL_CONFIG["MAX_K"]
    min_nei = FILL_CONFIG["MIN_NEI"]
    
    # Precompute k-ring cho tất cả các ô
    # Lưu ý: h3 v4 dùng grid_disk, v3 dùng k_ring. Code hỗ trợ v4.
    try:
        k_ring_map = {h: {k: list(h3.grid_disk(h, k)) for k in range(1, max_k + 1)} for h in h3_ids}
    except AttributeError:
        k_ring_map = {h: {k: list(h3.k_ring(h, k)) for k in range(1, max_k + 1)} for h in h3_ids}
    
    # Tạo map dữ liệu để tra cứu nhanh
    val_map = {(r.h3_index, r.date): getattr(r, col_name) for r in df.itertuples(index=False)}
    
    updates = []
    
    for date in dates:
        for h in h3_ids:
            key = (h, date)
            val = val_map.get(key)
            # Nếu đã có dữ liệu thì bỏ qua
            if pd.notna(val): continue
            
            found_val = None
            for k in range(1, max_k + 1):
                neighs = k_ring_map.get(h, {}).get(k, [])
                valid_vals = [val_map.get((n, date)) for n in neighs if pd.notna(val_map.get((n, date)))]
                
                if len(valid_vals) >= min_nei:
                    found_val = sum(valid_vals) / len(valid_vals)
                    break 
            
            if found_val is not None:
                val_map[key] = found_val
                updates.append((h, date, found_val))

    # Cập nhật lại DataFrame từ map
    # (Cách này nhanh hơn là gán từng dòng)
    df[col_name] = [val_map.get((r.h3_index, r.date)) for r in df.itertuples()]
    
    return df

# ---------------------------------------------------------
# CORE LOGIC: FINAL FILL (NEAREST NEIGHBOR)
# ---------------------------------------------------------
def fill_final_nearest(df, col_name):
    """
    Chiến lược cứu hộ cuối cùng (Last Resort):
    Tìm 1 ô hàng xóm gần nhất (Nearest Neighbor) trên toàn bản đồ có dữ liệu
    và sao chép dữ liệu sang ô bị thiếu.
    Dùng cho các đảo xa hoặc vùng mây quá lớn mà Spatial Fill (K-Ring) bó tay.
    """
    # 1. Kiểm tra xem còn thiếu không
    missing_mask = df[col_name].isna()
    if not missing_mask.any():
        return df
        
    print(f"   🔧 [Final Fill] Found {missing_mask.sum()} isolated cells. Running Nearest Neighbor...")

    # 2. Tách dữ liệu Tốt (Nguồn) và Xấu (Đích)
    bad_ids = df[missing_mask]["h3_index"].unique()
    all_ids = df["h3_index"].unique()
    # Good ids là những ô KHÔNG nằm trong bad_ids
    good_ids = list(set(all_ids) - set(bad_ids))

    if not good_ids: 
        return df

    # 3. Xây dựng cây tìm kiếm khoảng cách (KDTree)
    # Hỗ trợ cả H3 v3 và v4
    try:
        good_coords = [h3.cell_to_latlng(h) for h in good_ids]
        bad_coords = [h3.cell_to_latlng(h) for h in bad_ids]
    except AttributeError:
        good_coords = [h3.h3_to_geo(h) for h in good_ids]
        bad_coords = [h3.h3_to_geo(h) for h in bad_ids]
    
    tree = cKDTree(good_coords)
    # Tìm 1 điểm gần nhất (k=1)
    dists, indices = tree.query(bad_coords, k=1)

    # 4. Map ô Xấu -> ô Tốt gần nhất
    rescue_map = {bad_ids[i]: good_ids[indices[i]] for i in range(len(bad_ids))}

    # 5. Điền dữ liệu
    # Tạo dictionary tra cứu dữ liệu tốt: {(h3, date): value}
    df_good = df[df["h3_index"].isin(good_ids)]
    val_map = dict(zip(zip(df_good["h3_index"], df_good["date"]), df_good[col_name]))

    # Cập nhật giá trị
    def get_rescue_val(row):
        if pd.isna(row[col_name]):
            source_h3 = rescue_map.get(row["h3_index"])
            if source_h3:
                return val_map.get((source_h3, row["date"]), np.nan)
        return row[col_name]

    df[col_name] = df.apply(get_rescue_val, axis=1)
    
    # Fill nốt các lỗ hổng thời gian nếu ô nguồn cũng bị thiếu 1 vài ngày
    if df[col_name].isna().any():
         df[col_name] = df[col_name].interpolate(method='linear', limit_direction='both')

    return df

# ---------------------------------------------------------
# WORKER FUNCTION (Cho Multiprocessing)
# ---------------------------------------------------------
def process_single_dataset(args):
    """
    Hàm worker chạy trên Process riêng.
    Args: (key, spec, h3_data_bundle)
    """
    key, spec, h3_data_bundle = args
    print(f"🚀 [Start] {key.upper()} processing...")
    
    try:
        # 1. Extract
        df = extract_generic(key, spec, h3_data_bundle, DATA_RAW)
        if df.empty:
            print(f"⚠️ [Skip] {key.upper()} - No data found.")
            return key
            
        # 2. Check Missing & Cleanup
        col_name = spec["col_name"]
        # Convert rác thành NaN trước khi check
        if col_name in df.columns:
            df[col_name] = df[col_name].replace(-9999.0, np.nan)
            nan_raw = df[col_name].isna().sum()
        else:
            nan_raw = 0
        
        # 3. Fill Strategy
        if nan_raw > 0:
            # Bước A: Spatial Fill (Hàng xóm lân cận)
            df = fill_spatial_generic(df, col_name)
            
            # Bước B: Final Fill (Hàng xóm gần nhất toàn cục - Cứu đảo xa)
            nan_remaining = df[col_name].isna().sum()
            if nan_remaining > 0:
                df = fill_final_nearest(df, col_name)
            
        # 4. Save
        out_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        df.to_csv(out_path, index=False)
        print(f"✅ [Done] {key.upper()} saved.")
        
    except Exception as e:
        print(f"❌ [Error] {key.upper()}: {e}")
        raise e
        
    return key


# ---------------------------------------------------------
# MERGE FUNCTION
# ---------------------------------------------------------
from config import DATA_SPECS, DATA_PROCESSED

def merge_dynamic_datasets():
    """
    Gộp tất cả các file CSV thành phần (Mưa, Nhiệt, Ẩm...) thành 1 file tổng.
    Join key: ['h3_index', 'date']
    """
    print("🔄 [MERGE] Bắt đầu gộp các file dữ liệu...")
    
    # 1. Tập hợp danh sách file từ Config
    # Chỉ lấy những key có trong DATA_SPECS
    dfs = []
    
    for key, spec in DATA_SPECS.items():
        file_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        
        if not os.path.exists(file_path):
            print(f"⚠️ [Warning] File không tồn tại, bỏ qua: {spec['output_file']}")
            continue
            
        print(f"   📖 Reading {key}...")
        # Đọc file, ép kiểu h3_index về string để tránh lỗi merge
        df = pd.read_csv(file_path, dtype={'h3_index': str})
        
        # Đảm bảo cột date đúng định dạng
        # df['date'] = pd.to_datetime(df['date']) 
        
        # Set index là (h3_index, date) để chuẩn bị merge
        df = df.set_index(['h3_index', 'date'])
        dfs.append(df)
    
    if not dfs:
        print("❌ Không tìm thấy file dữ liệu nào để gộp!")
        return

    # 2. Thực hiện Merge (Join)
    # Dùng concat axis=1 sẽ nhanh hơn merge từng lần
    print("   🔗 Joining dataframes...")
    try:
        final_df = pd.concat(dfs, axis=1, join='outer')
        
        # Reset index để đưa h3_index và date trở lại thành cột
        final_df = final_df.reset_index()
        
        # 3. Lưu kết quả
        output_csv = os.path.join(DATA_PROCESSED, "FINAL_MERGED_DATASET.csv")
        # output_parquet = os.path.join(DATA_PROCESSED, "FINAL_MERGED_DATASET.parquet")
        
        print(f"   💾 Saving to {output_csv}...")
        final_df.to_csv(output_csv, index=False)
        # final_df.to_parquet(output_parquet, index=False) # Khuyên dùng Parquet nếu file lớn
        
        print(f"✅ [DONE] Đã gộp thành công! Kích thước: {final_df.shape}")
        return final_df
        
    except Exception as e:
        print(f"❌ [Error] Lỗi khi gộp file: {e}")
        return None



def extract_static_generic(spec_name, spec_config, h3_data_bundle, raw_root_dir):
    h3_ids, _, h3_geoms = h3_data_bundle
    
    folder_path = os.path.join(raw_root_dir, spec_config["folder"])
    file_path = os.path.join(folder_path, spec_config["file"])
    col_name = spec_config["col_name"]
    method = spec_config.get("method", "mean")

    if not os.path.exists(file_path):
        print(f"⚠️ Không tìm thấy file: {file_path}")
        return pd.DataFrame()

    gdf = gpd.GeoDataFrame({"h3_index": h3_ids}, geometry=h3_geoms, crs="EPSG:4326")

    # -------------------------------------------------------------
    # LOGIC 1: Lấy TẤT CẢ các lớp dưới dạng Tỷ lệ % (Fraction) VÀ GHI TÊN
    # -------------------------------------------------------------
    if method == "all_classes":
        print(f"   🌱 Đang tính toán tỷ lệ % cho tất cả các lớp {col_name}...")
        stats = zonal_stats(gdf, file_path, categorical=True)
        
        # Lấy từ điển dịch tên class từ config (nếu không có thì trả về dict rỗng)
        class_map = spec_config.get("class_names", {})
        
        records = []
        for s in stats:
            if not s: 
                records.append({})
            else:
                total_pixels = sum(s.values())
                row_data = {}
                for k, v in s.items():
                    # Tìm tên trong từ điển. Nếu file có mã lạ (ví dụ 99) mà chưa cấu hình, nó sẽ để tên là "99"
                    class_name = class_map.get(int(k), str(int(k)))
                    
                    # Tạo tên cột, ví dụ: "landcover_Water", "landcover_Rice"
                    column_key = f"{col_name}_{class_name}"
                    
                    row_data[column_key] = round(v / total_pixels, 4)
                records.append(row_data)
                
        df_out = pd.DataFrame(records)
        df_out = df_out.fillna(0) 
        df_out["h3_index"] = h3_ids
        
        cols = ["h3_index"] + [c for c in df_out.columns if c != "h3_index"]
        return df_out[cols]

    # -------------------------------------------------------------
    # LOGIC 2: Tính khoảng cách ngắn nhất đến sông (River Proximity)
    # -------------------------------------------------------------
    elif method == "min_distance":
        print(f"   🌊 Đang tính toán khoảng cách đến sông gần nhất...")
        with rasterio.open(file_path) as src:
            data = src.read(1)
            nodata = src.nodata
            
            # Lọc ra các pixel là sông (Giả sử sông có giá trị > 0)
            if nodata is not None:
                river_mask = (data > 0) & (data != nodata)
            else:
                river_mask = (data > 0)
                
            # Lấy tọa độ (row, col) của các pixel sông
            rows, cols = np.where(river_mask)
            
            if len(rows) == 0:
                print("   ⚠️ Lỗi: Không có pixel sông nào trong file TIF.")
                vals = [np.nan] * len(h3_ids)
            else:
                # Chuyển đổi từ (row, col) sang hệ tọa độ bản đồ (X, Y)
                xs, ys = rasterio.transform.xy(src.transform, rows, cols)
                river_coords = np.column_stack((xs, ys))
                
                # Tạo cây KDTree để tìm kiếm khoảng cách cực nhanh
                tree = cKDTree(river_coords)
                
                # Lấy tọa độ tâm của các ô lưới H3
                centroids = gdf.geometry.centroid
                h3_coords = np.column_stack((centroids.x, centroids.y))
                
                # Query khoảng cách ngắn nhất từ mỗi tâm H3 đến điểm sông gần nhất
                dists, _ = tree.query(h3_coords)
                
                # Quy đổi đơn vị: 
                # Nếu bản đồ là độ (EPSG:4326), 1 độ ~ 111.32 km.
                # Nếu bản đồ là mét (UTM), chia 1000 ra km.
                if src.crs and src.crs.is_geographic:
                    vals = dists * 111.32 
                else:
                    vals = dists / 1000.0
                    
        print(f"   ✅ Đã tính xong khoảng cách sông (Trung bình: {np.nanmean(vals):.2f} km)")

    # -------------------------------------------------------------
    # LOGIC 3: Zonal Stats cơ bản (mean, max, min cho DEM...)
    # -------------------------------------------------------------
    else:
        stats = zonal_stats(gdf, file_path, stats=method)
        vals = [s[method] if s[method] is not None else np.nan for s in stats]

    return pd.DataFrame({
        "h3_index": h3_ids,
        col_name: vals
    })

def process_single_static_dataset(args):
    """Worker chạy từng biến tĩnh độc lập."""
    key, spec, h3_data_bundle = args
    print(f"🚀 [Start] STATIC {key.upper()} processing...")
    
    try:
        df = extract_static_generic(key, spec, h3_data_bundle, DATA_RAW)
        if df.empty:
            print(f"⚠️ [Skip] STATIC {key.upper()} - Không tìm thấy file {spec['file']}.")
            return key
            
        out_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        df.to_csv(out_path, index=False)
        print(f"✅ [Done] STATIC {key.upper()} saved.")
        
    except Exception as e:
        print(f"❌ [Error] STATIC {key.upper()}: {e}")
        
    return key

def merge_static_datasets():
    """Gộp các file tĩnh riêng lẻ thành file DIM_H3_STATIC.csv.
    JOIN key: h3_index"""
    print("\n🔄 [MERGE-STATIC] Bắt đầu gộp các file dữ liệu tĩnh...")
    dfs = []
    
    for key, spec in STATIC_SPECS.items():
        file_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        if os.path.exists(file_path):
            print(f"   📖 Reading {key}...")
            df = pd.read_csv(file_path, dtype={'h3_index': str})
            df = df.set_index('h3_index')
            dfs.append(df)
            
    if dfs:
        final_static_df = pd.concat(dfs, axis=1, join='outer').reset_index()
        out_path = os.path.join(DATA_PROCESSED, "DIM_H3_STATIC.csv")
        final_static_df.to_csv(out_path, index=False)
        print(f"✅ [DONE] Đã lưu bảng danh mục tĩnh tại: {out_path} ({final_static_df.shape})")
    else:
        print("❌ Không có dữ liệu tĩnh nào để gộp.")