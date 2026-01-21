import os
import pandas as pd
import h3
from datetime import datetime, timedelta
from utils_h3 import index_files, sample_multiband_robust
from config import FILL_CONFIG, DATA_PROCESSED, DATA_RAW

# ---------------------------------------------------------
# CORE LOGIC
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
    
    # In ít lại để tránh loạn terminal khi chạy song song
    # print(f"   ⏳ Extracting {spec_name}...") 
    
    for (year, month), tif_path in sorted_items:
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


def fill_spatial_generic(df, col_name):
    if df.empty: return df
    
    h3_ids = df["h3_index"].unique()
    dates = df["date"].unique()
    max_k = FILL_CONFIG["MAX_K"]
    min_nei = FILL_CONFIG["MIN_NEI"]
    
    # Precompute k-ring
    k_ring_map = {h: {k: list(h3.grid_disk(h, k)) for k in range(1, max_k + 1)} for h in h3_ids}
    
    val_map = {(r.h3_index, r.date): getattr(r, col_name) for r in df.itertuples(index=False)}
    
    for date in dates:
        for h in h3_ids:
            key = (h, date)
            val = val_map.get(key)
            if pd.notna(val): continue
                
            for k in range(1, max_k + 1):
                neighs = k_ring_map[h][k]
                valid_vals = [val_map.get((n, date)) for n in neighs if pd.notna(val_map.get((n, date)))]
                
                if len(valid_vals) >= min_nei:
                    val_map[key] = sum(valid_vals) / len(valid_vals)
                    break 
    
    df[col_name] = [val_map.get((r.h3_index, r.date)) for r in df.itertuples()]
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
            
        # 2. Check Missing
        nan_raw = df[spec["col_name"]].isna().sum()
        
        # 3. Fill
        if nan_raw > 0:
            df = fill_spatial_generic(df, spec["col_name"])
            
        # 4. Save
        out_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        df.to_csv(out_path, index=False)
        print(f"✅ [Done] {key.upper()} saved.")
        
    except Exception as e:
        print(f"❌ [Error] {key.upper()}: {e}")
        raise e
        
    return key