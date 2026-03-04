"""
===============================================================================
MRC MERGE YEAR (MÙA MƯA) - Lấy dữ liệu mùa mưa/mùa lũ
===============================================================================
Mùa mưa/lũ ĐBSCL theo MRC: Nov-May (tháng 11 năm trước đến tháng 5 năm sau)
"""
import pandas as pd
import numpy as np
import argparse
import re
import calendar
from datetime import datetime, timedelta

# ============================================================================
# CẤU HÌNH
# ============================================================================
TARGET_YEAR = 2025
INPUT_FILE = "cdo_seasonal_raw.csv" 
OUTPUT_FILE = None

# Các tháng mùa mưa/lũ (theo MRC FFW)
RAINY_MONTHS = [1, 2, 3, 4, 5, 11, 12]  # Jan-May + Nov-Dec


def get_year_columns(df: pd.DataFrame) -> list:
    """Lấy danh sách các cột năm thủy văn"""
    year_cols = []
    for col in df.columns:
        if re.match(r'^\d{4}\.\d{2}$', str(col)):
            year_cols.append(col)
    return sorted(year_cols)


def extract_rainy_season_data(df: pd.DataFrame, target_year: int) -> pd.DataFrame:
    """
    Trích xuất dữ liệu MÙA MƯA cho một năm
    Chỉ lấy các tháng: 1-5 và 11-12
    Dữ liệu thực từ MRC, không ước tính
    """
    df = df.copy()
    df['date_gmt'] = pd.to_datetime(df['date_gmt'], errors='coerce')
    df = df.dropna(subset=['date_gmt'])
    
    year_cols = get_year_columns(df)
    print(f"Các năm thủy văn có sẵn: {', '.join(year_cols)}")
    
    # Xác định cột cần dùng
    jan_may_col = f"{target_year - 1}.{str(target_year)[-2:]}"  # 2024.25 cho Jan-May 2025
    nov_dec_col = f"{target_year}.{str(target_year + 1)[-2:]}"  # 2025.26 cho Nov-Dec 2025
    
    print(f"\nNăm {target_year} (MÙA MƯA):")
    print(f"  - Jan-May: lấy từ cột {jan_may_col}")
    print(f"  - Nov-Dec: lấy từ cột {nov_dec_col}")
    
    results = []
    
    # ========================================================================
    # 1. Jan-May: Từ cột năm thủy văn trước
    # ========================================================================
    if jan_may_col in df.columns:
        df_jan_may = df[df['date_gmt'].dt.month.isin([1, 2, 3, 4, 5])].copy()
        
        for _, row in df_jan_may.iterrows():
            val = row.get(jan_may_col)
            if pd.notna(val):
                try:
                    orig_date = row['date_gmt']
                    if orig_date.month == 2 and orig_date.day == 29:
                        if not calendar.isleap(target_year):
                            continue
                    date = orig_date.replace(year=target_year)
                    results.append({
                        'date_gmt': date.strftime('%Y-%m-%d'),
                        'water_level': round(val, 2)
                    })
                except ValueError:
                    continue
        
        print(f"  → Jan-May: {len(results)} ngày")
    else:
        print(f"  ⚠ Không có cột {jan_may_col}")
    
    jan_may_count = len(results)
    
    # ========================================================================
    # 2. Nov-Dec: Từ cột năm thủy văn hiện tại
    # ========================================================================
    if nov_dec_col in df.columns:
        df_nov_dec = df[df['date_gmt'].dt.month.isin([11, 12])].copy()
        
        for _, row in df_nov_dec.iterrows():
            val = row.get(nov_dec_col)
            if pd.notna(val):
                results.append({
                    'date_gmt': row['date_gmt'].strftime('%Y-%m-%d'),
                    'water_level': round(val, 2)
                })
        
        nov_dec_count = len(results) - jan_may_count
        print(f"  → Nov-Dec: {nov_dec_count} ngày")
    else:
        print(f"  ⚠ Không có cột {nov_dec_col}")
    
    # Tạo DataFrame và sắp xếp
    df_result = pd.DataFrame(results)
    df_result['date_gmt'] = pd.to_datetime(df_result['date_gmt'])
    df_result = df_result.sort_values('date_gmt')
    df_result = df_result.drop_duplicates(subset=['date_gmt'])
    
    # ========================================================================
    # Fill các ngày thiếu với giá trị 0
    # ========================================================================
    print(f"\n  → Kiểm tra ngày thiếu...")
    
    # Tạo full date range cho mùa mưa
    all_dates = []
    
    # Jan-May của năm target
    for month in [1, 2, 3, 4, 5]:
        days_in_month = calendar.monthrange(target_year, month)[1]
        for day in range(1, days_in_month + 1):
            all_dates.append(datetime(target_year, month, day))
    
    # Nov-Dec của năm target
    for month in [11, 12]:
        days_in_month = calendar.monthrange(target_year, month)[1]
        for day in range(1, days_in_month + 1):
            all_dates.append(datetime(target_year, month, day))
    
    df_full = pd.DataFrame({'date_gmt': all_dates})
    
    # Merge để tìm ngày thiếu
    df_result = df_full.merge(df_result, on='date_gmt', how='left')
    
    # Đếm ngày thiếu
    missing_count = df_result['water_level'].isna().sum()
    
    if missing_count > 0:
        print(f"    Có {missing_count} ngày thiếu dữ liệu → đặt = 0")
        df_result['water_level'] = df_result['water_level'].fillna(0)
    else:
        print(f"    Không có ngày thiếu")
    
    # Format output
    df_result = df_result.sort_values('date_gmt')
    df_result['date_gmt'] = df_result['date_gmt'].dt.strftime('%Y-%m-%d')
    df_result = df_result.reset_index(drop=True)
    
    return df_result


def main():
    parser = argparse.ArgumentParser(description='Lấy dữ liệu mùa mưa')
    parser.add_argument('--year', type=int, default=TARGET_YEAR)
    parser.add_argument('--input', type=str, default=INPUT_FILE)
    parser.add_argument('--output', type=str, default=OUTPUT_FILE)
    args = parser.parse_args()
    
    year = args.year
    input_file = args.input
    output_file = args.output
    
    print("="*70)
    print("MRC - DỮ LIỆU MÙA MƯA/LŨ")
    print("="*70)
    print(f"Năm: {year}")
    print(f"Các tháng: {RAINY_MONTHS}")
    print(f"Input: {input_file}")
    print("="*70)
    
    # Load data
    try:
        df = pd.read_csv(input_file)
        print(f"\n✓ Đã load {len(df)} bản ghi từ {input_file}")
    except FileNotFoundError:
        print(f"\n✗ Không tìm thấy file: {input_file}")
        return
    
    # Extract data
    df_year = extract_rainy_season_data(df, year)
    
    # Output file
    if output_file is None:
        station = input_file.replace('_seasonal_raw.csv', '').replace('_seasonal.csv', '')
        output_file = f"{station}_{year}_rainy.csv"
    
    # Save
    df_year.to_csv(output_file, index=False)
    
    print("\n" + "="*70)
    print("KẾT QUẢ")
    print("="*70)
    print(f"\n✓ Đã lưu: {output_file}")
    print(f"  Số bản ghi: {len(df_year)}")
    print(f"  Format: date_gmt, water_level")
    
    # Thống kê
    df_year['date_gmt'] = pd.to_datetime(df_year['date_gmt'])
    df_year['month'] = df_year['date_gmt'].dt.month
    
    print(f"\n  Phân bố theo tháng:")
    stats = df_year.groupby('month')['water_level'].agg(['count', 'min', 'mean', 'max'])
    for month, row in stats.iterrows():
        print(f"    Tháng {month:2d}: {int(row['count']):3d} ngày | Min: {row['min']:5.2f}m | TB: {row['mean']:5.2f}m | Max: {row['max']:5.2f}m")
    
    # Mẫu dữ liệu
    print("\n--- 10 dòng đầu ---")
    df_year['date_gmt'] = df_year['date_gmt'].dt.strftime('%Y-%m-%d')
    print(df_year[['date_gmt', 'water_level']].head(10).to_string(index=False))
    
    print("\n--- 10 dòng cuối ---")
    print(df_year[['date_gmt', 'water_level']].tail(10).to_string(index=False))
    
    print("\n" + "="*70)
    print("GHI CHÚ")
    print("="*70)
    print(f"""

""")
    
    return df_year


if __name__ == "__main__":
    main()
