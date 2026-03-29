"""
Script so sanh ket qua giua 2 thu muc processed (truoc va sau khi toi uu)
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

def compare_csv_files(file1, file2, tolerance=1e-6):
    """
    So sanh 2 file CSV va tra ve thong ke chi tiet
    """
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    result = {
        'file': os.path.basename(file1),
        'rows_match': len(df1) == len(df2),
        'df1_rows': len(df1),
        'df2_rows': len(df2),
        'df1_cols': list(df1.columns),
        'df2_cols': list(df2.columns),
    }

    # So sanh cot (bo qua thu tu)
    result['cols_match'] = set(df1.columns) == set(df2.columns)

    if not result['rows_match'] or not result['cols_match']:
        result['identical'] = False
        return result

    # QUAN TRONG: Merge theo key columns de so sanh dung
    key_cols = []
    if 'h3_index' in df1.columns:
        key_cols.append('h3_index')
    if 'date' in df1.columns:
        key_cols.append('date')

    if key_cols:
        # Sort theo key truoc khi so sanh
        df1 = df1.sort_values(key_cols).reset_index(drop=True)
        df2 = df2.sort_values(key_cols).reset_index(drop=True)

        # Kiem tra key co khop khong
        for kc in key_cols:
            if not (df1[kc] == df2[kc]).all():
                result['identical'] = False
                result['key_mismatch'] = kc
                return result

    # So sanh tung cot (chi so sanh cot chung, bo qua key cols)
    col_stats = {}
    all_match = True
    common_cols = set(df1.columns) & set(df2.columns)

    for col in common_cols:
        if col in key_cols:
            continue  # Da kiem tra o tren

        if df1[col].dtype == 'object':
            # So sanh exact cho cot string
            match = (df1[col] == df2[col]).all()
            col_stats[col] = {'type': 'string', 'exact_match': match}
            if not match:
                all_match = False
        else:
            # So sanh numeric voi tolerance
            v1 = df1[col].values.astype(float)
            v2 = df2[col].values.astype(float)

            # Xu ly NaN
            nan1 = np.isnan(v1)
            nan2 = np.isnan(v2)
            nan_match = (nan1 == nan2).all()

            # So sanh gia tri khong phai NaN
            mask = ~nan1 & ~nan2
            if mask.sum() > 0:
                diff = np.abs(v1[mask] - v2[mask])
                max_diff = diff.max()
                mean_diff = diff.mean()

                # Correlation
                if len(v1[mask]) > 1:
                    corr = np.corrcoef(v1[mask], v2[mask])[0, 1]
                else:
                    corr = 1.0

                # RMSE
                rmse = np.sqrt(np.mean(diff ** 2))

                # Check tolerance
                within_tol = max_diff <= tolerance

                col_stats[col] = {
                    'type': 'numeric',
                    'nan_match': nan_match,
                    'nan_count_df1': nan1.sum(),
                    'nan_count_df2': nan2.sum(),
                    'max_diff': max_diff,
                    'mean_diff': mean_diff,
                    'rmse': rmse,
                    'correlation': corr,
                    'within_tolerance': within_tol,
                    'n_compared': mask.sum()
                }

                if not within_tol or not nan_match:
                    all_match = False
            else:
                col_stats[col] = {
                    'type': 'numeric',
                    'nan_match': nan_match,
                    'all_nan': True
                }

    result['col_stats'] = col_stats
    result['identical'] = all_match

    return result

def compare_directories(dir1, dir2, tolerance=1e-6):
    """
    So sanh tat ca file CSV trong 2 thu muc
    """
    dir1 = Path(dir1)
    dir2 = Path(dir2)

    # Tim tat ca file CSV
    files1 = set(f.name for f in dir1.glob('*.csv'))
    files2 = set(f.name for f in dir2.glob('*.csv'))

    print("=" * 70)
    print(f"SO SANH KET QUA")
    print("=" * 70)
    print(f"Thu muc 1 (TRUOC): {dir1}")
    print(f"Thu muc 2 (SAU):   {dir2}")
    print(f"Tolerance: {tolerance}")
    print("=" * 70)

    # File chi co trong 1 thu muc
    only_in_1 = files1 - files2
    only_in_2 = files2 - files1
    common = files1 & files2

    if only_in_1:
        print(f"\n[!] File chi co trong thu muc 1: {only_in_1}")
    if only_in_2:
        print(f"\n[!] File chi co trong thu muc 2: {only_in_2}")

    print(f"\n[i] So file chung: {len(common)}")
    print("-" * 70)

    results = []

    for fname in sorted(common):
        file1 = dir1 / fname
        file2 = dir2 / fname

        print(f"\nDang so sanh: {fname}")

        try:
            result = compare_csv_files(file1, file2, tolerance)
            results.append(result)

            if result['identical']:
                print(f"  [OK] Ket qua GIONG NHAU (trong tolerance)")
            else:
                print(f"  [!!] Ket qua KHAC NHAU")

                if not result['rows_match']:
                    print(f"       - So dong khac: {result['df1_rows']} vs {result['df2_rows']}")

                if not result['cols_match']:
                    print(f"       - Cot khac nhau")
                    print(f"         DF1: {result['df1_cols']}")
                    print(f"         DF2: {result['df2_cols']}")

                if 'col_stats' in result:
                    for col, stats in result['col_stats'].items():
                        if stats['type'] == 'numeric' and not stats.get('within_tolerance', True):
                            print(f"       - Cot '{col}':")
                            print(f"         Max diff: {stats['max_diff']:.8f}")
                            print(f"         Mean diff: {stats['mean_diff']:.8f}")
                            print(f"         RMSE: {stats['rmse']:.8f}")
                            print(f"         Correlation: {stats['correlation']:.8f}")

                        if stats['type'] == 'numeric' and not stats.get('nan_match', True):
                            print(f"       - Cot '{col}' co so NaN khac:")
                            print(f"         DF1: {stats['nan_count_df1']} NaN")
                            print(f"         DF2: {stats['nan_count_df2']} NaN")

        except Exception as e:
            print(f"  [ERROR] Loi khi so sanh: {e}")
            results.append({'file': fname, 'error': str(e)})

    # Tong ket
    print("\n" + "=" * 70)
    print("TONG KET")
    print("=" * 70)

    success = sum(1 for r in results if r.get('identical', False))
    failed = len(results) - success

    print(f"Tong so file so sanh: {len(results)}")
    print(f"  - Giong nhau: {success}")
    print(f"  - Khac nhau:  {failed}")

    if failed == 0:
        print("\n[OK] TAT CA KET QUA GIONG NHAU!")
        print("     Code toi uu cho ket qua CHINH XAC.")
    else:
        print(f"\n[!!] Co {failed} file cho ket qua KHAC.")
        print("     Can kiem tra lai logic toi uu.")

    return results

def main():
    if len(sys.argv) < 3:
        print("Cach dung: python compare_results.py <dir_truoc> <dir_sau> [tolerance]")
        print("")
        print("Vi du:")
        print("  python compare_results.py data/processed_old data/processed 1e-6")
        sys.exit(1)

    dir1 = sys.argv[1]
    dir2 = sys.argv[2]
    tolerance = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6

    if not os.path.isdir(dir1):
        print(f"Loi: Thu muc khong ton tai: {dir1}")
        sys.exit(1)

    if not os.path.isdir(dir2):
        print(f"Loi: Thu muc khong ton tai: {dir2}")
        sys.exit(1)

    compare_directories(dir1, dir2, tolerance)

if __name__ == "__main__":
    main()
