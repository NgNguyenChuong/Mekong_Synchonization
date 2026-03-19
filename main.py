#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DGGS Pipeline CLI - Giao dien dong lenh voi cac tuy chon

Cach dung:
    python run.py                           # Chay toan bo (mac dinh)
    python run.py --from 2024-01 --to 2024-06  # Chi extract tu thang 1 den thang 6/2024
    python run.py --month 2024-03           # Chi extract thang 3/2024
    python run.py --skip-static             # Bo qua xu ly du lieu tinh
    python run.py --skip-dynamic            # Bo qua xu ly du lieu dong
    python run.py --datasets rain,temp_avg  # Chi xu ly cac dataset cu the
    python run.py --workers 4               # So luong worker (mac dinh: CPU - 1)
    python run.py --no-fill                 # Khong fill missing data
    python run.py --dry-run                 # Chi hien thi ke hoach, khong chay
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Fix Unicode on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from concurrent.futures import ProcessPoolExecutor
from config import (
    DATA_SPECS, H3_GRID_GEOJSON, CRS_METRIC, CRS_WGS84, DATA_RAW, STATIC_SPECS, DATA_PROCESSED
)
from utils_h3 import load_h3_multipoints
from preprocessing import run_preprocessing


def parse_month(s):
    """Parse YYYY-MM string to (year, month) tuple"""
    try:
        parts = s.split('-')
        return int(parts[0]), int(parts[1])
    except:
        raise argparse.ArgumentTypeError(f"Invalid month format: {s}. Use YYYY-MM")


def filter_files_by_date(file_map, from_date=None, to_date=None, single_month=None):
    """
    Loc file theo khoang thoi gian

    Args:
        file_map: dict {(year, month): path}
        from_date: (year, month) tuple - bat dau
        to_date: (year, month) tuple - ket thuc
        single_month: (year, month) tuple - chi 1 thang

    Returns:
        filtered dict
    """
    if single_month:
        return {k: v for k, v in file_map.items() if k == single_month}

    if from_date is None and to_date is None:
        return file_map

    filtered = {}
    for (year, month), path in file_map.items():
        # Convert to comparable format YYYYMM
        ym = year * 100 + month

        if from_date:
            from_ym = from_date[0] * 100 + from_date[1]
            if ym < from_ym:
                continue

        if to_date:
            to_ym = to_date[0] * 100 + to_date[1]
            if ym > to_ym:
                continue

        filtered[(year, month)] = path

    return filtered


def process_single_dataset_with_options(args):
    """
    Worker function voi cac tuy chon
    """
    key, spec, h3_data_bundle, options = args

    from processing import fill_spatial_generic, fill_final_nearest
    from utils_h3 import index_files, sample_multiband_robust
    from datetime import datetime, timedelta
    import pandas as pd

    print(f"🚀 [Start] {key.upper()} processing...")

    try:
        # 1. Extract
        h3_ids, point_groups, h3_geoms = h3_data_bundle
        input_dir = os.path.join(DATA_RAW, spec["folder"])
        col_name = spec["col_name"]

        file_map = index_files(input_dir)
        if not file_map:
            return None

        # Loc theo thoi gian
        file_map = filter_files_by_date(
            file_map,
            from_date=options.get('from_date'),
            to_date=options.get('to_date'),
            single_month=options.get('single_month')
        )

        if not file_map:
            print(f"   ⚠️ No files match date filter for {key}")
            return None

        print(f"   📁 Processing {len(file_map)} month(s) for {key}")

        records = []
        sorted_items = sorted(file_map.items())

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

        df = pd.DataFrame(records)

        # 2. Fill (neu khong bi skip)
        if not options.get('no_fill', False):
            df = fill_spatial_generic(df, col_name)
            df = fill_final_nearest(df, col_name)

        # 3. Save
        output_path = os.path.join(DATA_PROCESSED, spec["output_file"])
        df.to_csv(output_path, index=False)
        print(f"✅ [Done] {key.upper()} -> {output_path}")

        return output_path

    except Exception as e:
        print(f"❌ [Error] {key}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description='DGGS H3 Pipeline - Extract va Fill du lieu dia khong gian',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Vi du su dung:
  python run.py                              # Chay toan bo
  python run.py --month 2024-03              # Chi thang 3/2024
  python run.py --from 2024-01 --to 2024-06  # Tu thang 1 den 6/2024
  python run.py --datasets rain,solar        # Chi xu ly rain va solar
  python run.py --skip-static --no-fill      # Skip static, khong fill
  python run.py --dry-run                    # Xem ke hoach truoc
        """
    )

    # Date filters
    date_group = parser.add_argument_group('Date Filters')
    date_group.add_argument('--from', dest='from_date', type=parse_month, metavar='YYYY-MM',
                           help='Thang bat dau (vd: 2024-01)')
    date_group.add_argument('--to', dest='to_date', type=parse_month, metavar='YYYY-MM',
                           help='Thang ket thuc (vd: 2024-12)')
    date_group.add_argument('--month', dest='single_month', type=parse_month, metavar='YYYY-MM',
                           help='Chi xu ly 1 thang cu the (vd: 2024-03)')

    # Dataset selection
    data_group = parser.add_argument_group('Dataset Selection')
    data_group.add_argument('--datasets', type=str, metavar='LIST',
                           help='Danh sach dataset can xu ly, cach nhau boi dau phay (vd: rain,solar,temp_avg)')
    data_group.add_argument('--skip-static', action='store_true',
                           help='Bo qua xu ly du lieu tinh (DEM, landcover, river)')
    data_group.add_argument('--skip-dynamic', action='store_true',
                           help='Bo qua xu ly du lieu dong (rain, temp, solar...)')

    # Processing options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('--no-fill', action='store_true',
                           help='Khong fill missing data (chi extract)')
    proc_group.add_argument('--no-merge', action='store_true',
                           help='Khong merge cac dataset thanh file tong hop')
    proc_group.add_argument('--skip-preprocess', action='store_true',
                           help='Bo qua buoc preprocessing (neu da chay truoc do)')

    # Performance
    perf_group = parser.add_argument_group('Performance')
    perf_group.add_argument('--workers', type=int, default=None, metavar='N',
                           help='So luong worker song song (mac dinh: CPU cores - 1)')

    # Utility
    util_group = parser.add_argument_group('Utility')
    util_group.add_argument('--dry-run', action='store_true',
                           help='Chi hien thi ke hoach, khong thuc su chay')
    util_group.add_argument('--list-datasets', action='store_true',
                           help='Liet ke cac dataset co san')

    args = parser.parse_args()

    # List datasets
    if args.list_datasets:
        print("\n📊 DYNAMIC DATASETS (du lieu theo thoi gian):")
        print("-" * 50)
        for key, spec in DATA_SPECS.items():
            folder = os.path.join(DATA_RAW, spec["folder"])
            exists = "✅" if os.path.exists(folder) else "❌"
            print(f"  {exists} {key:15} -> {spec['folder']}/")

        print("\n🗺️  STATIC DATASETS (du lieu tinh):")
        print("-" * 50)
        for key, spec in STATIC_SPECS.items():
            path = os.path.join(DATA_RAW, spec["folder"], spec["file"])
            exists = "✅" if os.path.exists(path) else "❌"
            print(f"  {exists} {key:15} -> {spec['folder']}/{spec['file']}")

        return

    # Build options dict
    options = {
        'from_date': args.from_date,
        'to_date': args.to_date,
        'single_month': args.single_month,
        'no_fill': args.no_fill,
    }

    # Filter datasets
    selected_datasets = None
    if args.datasets:
        selected_datasets = [d.strip() for d in args.datasets.split(',')]

    start_time = time.time()

    print("=" * 60)
    print("🚀 DGGS H3 PIPELINE")
    print("=" * 60)

    # Show plan
    print("\n📋 KE HOACH XU LY:")
    print("-" * 40)

    if args.single_month:
        print(f"   📅 Thoi gian: Chi thang {args.single_month[0]}-{args.single_month[1]:02d}")
    elif args.from_date or args.to_date:
        from_str = f"{args.from_date[0]}-{args.from_date[1]:02d}" if args.from_date else "dau"
        to_str = f"{args.to_date[0]}-{args.to_date[1]:02d}" if args.to_date else "cuoi"
        print(f"   📅 Thoi gian: Tu {from_str} den {to_str}")
    else:
        print(f"   📅 Thoi gian: Tat ca cac thang co san")

    if not args.skip_dynamic:
        if selected_datasets:
            print(f"   📊 Dynamic datasets: {', '.join(selected_datasets)}")
        else:
            print(f"   📊 Dynamic datasets: Tat ca ({len(DATA_SPECS)} loai)")
    else:
        print(f"   📊 Dynamic datasets: SKIP")

    if not args.skip_static:
        print(f"   🗺️  Static datasets: Tat ca ({len(STATIC_SPECS)} loai)")
    else:
        print(f"   🗺️  Static datasets: SKIP")

    print(f"   🔧 Fill missing: {'Khong' if args.no_fill else 'Co'}")
    print(f"   🔗 Merge: {'Khong' if args.no_merge else 'Co'}")

    if args.dry_run:
        print("\n⚠️  DRY RUN - Khong thuc su chay")
        return

    print("-" * 40)

    # 1. PREPROCESSING
    if not args.skip_preprocess:
        try:
            run_preprocessing()
        except Exception as e:
            print(f"❌ Preprocessing failed: {e}")
            return

    # 2. LOAD GRID
    print("\n[STEP 1] Loading H3 Grid Geometry...")
    if not os.path.exists(H3_GRID_GEOJSON):
        print("❌ Grid file missing. Run without --skip-preprocess first.")
        return

    h3_data_bundle = load_h3_multipoints(H3_GRID_GEOJSON, CRS_METRIC, CRS_WGS84)
    print(f"✅ Loaded {len(h3_data_bundle[0])} cells.")

    # 3. PREPARE TASKS
    tasks = []
    static_tasks = []

    if not args.skip_dynamic:
        for key, spec in DATA_SPECS.items():
            if selected_datasets and key not in selected_datasets:
                continue

            input_dir = os.path.join(DATA_RAW, spec["folder"])
            if not os.path.exists(input_dir):
                print(f"⚠️ [Skip] {key.upper()} - folder not found")
                continue

            tasks.append((key, spec, h3_data_bundle, options))

    if not args.skip_static:
        from processing import process_single_static_dataset
        for key, spec in STATIC_SPECS.items():
            input_path = os.path.join(DATA_RAW, spec["folder"], spec["file"])
            if not os.path.exists(input_path):
                print(f"⚠️ [Skip] Static {key.upper()} - file not found")
                continue
            static_tasks.append((key, spec, h3_data_bundle))

    # 4. PARALLEL PROCESSING
    max_workers = args.workers or max(1, (os.cpu_count() or 1) - 1)
    print(f"\n[STEP 2] Processing with {max_workers} workers...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        if tasks:
            list(executor.map(process_single_dataset_with_options, tasks))

        if static_tasks:
            from processing import process_single_static_dataset
            list(executor.map(process_single_static_dataset, static_tasks))

    # 5. MERGE
    if not args.no_merge:
        print("\n[STEP 3] Merging datasets...")
        from processing import merge_dynamic_datasets, merge_static_datasets

        if not args.skip_dynamic:
            merge_dynamic_datasets()
        if not args.skip_static:
            merge_static_datasets()

    print("\n" + "=" * 60)
    print(f"✅ PIPELINE FINISHED in {time.time() - start_time:.1f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    main()
