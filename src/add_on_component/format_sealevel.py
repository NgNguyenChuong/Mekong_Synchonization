import pandas as pd
import re

def format_cmems_csv(input_path, output_path=None):
    """
    Format CMEMS CSV file, extract lat/lon from header and add to data.
    Output: time, lat, lon, adt
    """
    # Đọc dòng 5 để lấy tọa độ
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    # Parse POINT (lon lat) từ dòng 5
    geometry_line = lines[4]  # dòng 5 (index 4)
    match = re.search(r'POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)', geometry_line)
    
    if not match:
        raise ValueError(f"Không tìm thấy POINT trong: {geometry_line}")
    
    lon = float(match.group(1))
    lat = float(match.group(2))
    
    # Đọc data từ dòng 8 (skip 7 dòng header)
    df = pd.read_csv(input_path, skiprows=7)
    
    # Thêm cột lat, lon
    df['lat'] = lat
    df['lon'] = lon
    
    # Sắp xếp lại cột: time, lat, lon, adt
    df = df[['time', 'lat', 'lon', 'adt']]
    
    # Lưu file
    if output_path is None:
        output_path = input_path.replace('.csv', '_formatted.csv')
    
    df.to_csv(output_path, index=False)
    print(f"✅ Đã lưu: {output_path}")
    print(f"   Tọa độ: ({lat}, {lon}) | Số dòng: {len(df)}")
    
    return df


if __name__ == "__main__":
    input_file = "./data/water/raw/cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D_1774800689029.csv"
    df = format_cmems_csv(input_file)
    print(df.head())
