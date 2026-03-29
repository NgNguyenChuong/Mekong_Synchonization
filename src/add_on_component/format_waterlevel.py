import pandas as pd
import os


def format_water_csv(input_path, output_path=None):
    """
    Format water CSV file, add location info of this station.
    lct is extracted from 3rd part of filename (e.g., water_level_CDO_20260328.csv -> CDO)
    """
    
    # Lấy tên file và trích xuất lct (phần thứ 3, tách bởi '_')
    filename = os.path.basename(input_path)
    parts = filename.replace('.csv', '').split('_')
    lct = parts[2] if len(parts) > 2 else "UNKNOWN"
    
    # Đọc data (file này không có header phụ)
    df = pd.read_csv(input_path)
    
    # Thêm cột lct
    df['lct'] = lct
 
    # Sắp xếp lại cột: dd-mm-yy, lct, value
    df = df[['dd-mm-yy', 'lct', 'value']]
    
    # Lưu file
    if output_path is None:
        output_path = input_path.replace('.csv', '_formatted.csv')
    
    df.to_csv(output_path, index=False)
    print(f"✅ Đã lưu: {output_path}")
    print(f"   Location: {lct} | Số dòng: {len(df)}")
    
    return df



if __name__ == "__main__":
    input_file = "./data/water/raw/water_level_TCH_20260328.csv"
    df = format_water_csv(input_file)
    print(df.head())
