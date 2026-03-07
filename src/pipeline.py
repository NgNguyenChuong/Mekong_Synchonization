import os
import time
from concurrent.futures import ProcessPoolExecutor
from config import (
    DATA_SPECS, H3_GRID_GEOJSON, CRS_METRIC, CRS_WGS84, DATA_RAW
)
from utils_h3 import load_h3_multipoints
from preprocessing import run_preprocessing
from processing import process_single_dataset, merge_all_datasets


def main():
    start_time = time.time()
    print("==================================================")
    print("🚀 STARTING PARALLEL H3 PIPELINE")
    print("==================================================")
    
    # 1. PREPROCESSING (Vẫn chạy tuần tự vì cần file này để chạy tiếp)
    try:
        run_preprocessing()
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        return

    # 2. LOAD GRID (Load 1 lần ở Main Process)
    print("\n[STEP 1] Loading H3 Grid Geometry...")
    if not os.path.exists(H3_GRID_GEOJSON):
        print("❌ Grid file missing.")
        return

    # H3 Data Bundle sẽ được copy sang các process con (nhờ cơ chế của Python)
    h3_data_bundle = load_h3_multipoints(H3_GRID_GEOJSON, CRS_METRIC, CRS_WGS84)
    print(f"✅ Loaded {len(h3_data_bundle[0])} cells. Ready to fork.")

    # 3. PARALLEL PROCESSING
    print("\n[STEP 2] Launching Parallel Workers...")
    
    # Chuẩn bị danh sách tham số để đẩy vào Pool
    # Mỗi worker cần: key, config của key đó, và dữ liệu grid
    tasks = []
    for key, spec in DATA_SPECS.items():
        input_dir = os.path.join(DATA_RAW, spec["folder"])
        if not os.path.exists(input_dir):
            print(f"⚠️ [Skip] {key.upper()} - folder not found: {input_dir}")
            continue
        tasks.append((key, spec, h3_data_bundle))

    if not tasks:
        print("❌ No valid dataset folders found. Nothing to process.")
        return

    # SỐ LUỒNG TỐI ĐA (max_workers)
    # Nếu máy bạn 8 core, để 4-6 là đẹp. Nếu RAM yếu thì giảm xuống.
    # Mặc định None = số core của máy.
    MAX_WORKERS = max(1, (os.cpu_count() or 1) - 1)  # Leave one core for system
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map hàm worker với danh sách tasks
        results = list(executor.map(process_single_dataset, tasks))
    
    # --- MERGE CSV ---
    print("\n[STEP 3] Merging all datasets...")
    merge_all_datasets()
    # ---------------------

    print("\n==================================================")
    print(f"✅ PIPELINE FINISHED in {time.time() - start_time:.1f} seconds")
    print("==================================================")

if __name__ == "__main__":
    # BẮT BUỘC PHẢI CÓ DÒNG NÀY TRÊN WINDOWS ĐỂ CHẠY MULTIPROCESSING
    main()