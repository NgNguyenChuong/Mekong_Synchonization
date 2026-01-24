import os
import time
from concurrent.futures import ProcessPoolExecutor
from config import (
    DATA_SPECS, H3_GRID_GEOJSON, CRS_METRIC, CRS_WGS84
)
from utils_h3 import load_h3_multipoints
from preprocessing import run_preprocessing
from processing import process_single_dataset, merge_all_datasets # <--- Thêm merge_all_datasets
def main():
    
    # --- MERGE CSV ---
    print("\n[STEP 3] Merging all datasets...")
    merge_all_datasets()
    # ---------------------
if __name__ == "__main__":
    # BẮT BUỘC PHẢI CÓ DÒNG NÀY TRÊN WINDOWS ĐỂ CHẠY MULTIPROCESSING
    main()