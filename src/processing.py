import os
import pandas as pd
import numpy as np
import h3
from scipy.spatial import cKDTree
from datetime import datetime, timedelta
from utils_h3 import index_files, sample_multiband_robust
from config import FILL_CONFIG, DATA_PROCESSED, DATA_RAW

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

def merge_all_datasets():
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