# DGGS H3 Pipeline - Documentation

## Tổng quan

**Mekong_DGGS** là một pipeline xử lý dữ liệu địa không gian sử dụng hệ thống lưới lục giác **H3** (Discrete Global Grid System) cho vùng **Đồng bằng sông Cửu Long (ĐBSCL)**.

Pipeline chuyển đổi dữ liệu raster (GeoTIFF) và vector (Shapefile) thành dữ liệu tabular theo các ô lục giác H3, phục vụ cho phân tích và mô hình hóa.

---

## Cấu trúc thư mục

```
Mekong_DGGS/
├── main.py                 # Entry point - chạy toàn bộ pipeline
├── requirements.txt        # Các thư viện Python cần thiết
├── src/
│   ├── config.py           # Cấu hình đường dẫn và dataset specs
│   ├── preprocessing.py    # Tiền xử lý: tạo lưới H3
│   ├── processing.py       # Xử lý chính: extract, fill, merge
│   ├── utils_h3.py         # Các hàm tiện ích cho H3
│   └── add_on_component/   # Các module bổ sung
│       ├── draw_h3.py          # Vẽ lưới H3
│       ├── getWaterLevel.py    # Lấy dữ liệu mực nước
│       ├── mrc_merge_year_rainy.py  # Merge dữ liệu mưa MRC
│       └── readcsv.py          # Đọc file CSV
├── data/
│   ├── raw/                # Dữ liệu thô (input)
│   └── processed/          # Dữ liệu đã xử lý (output)
├── notebooks/              # Jupyter notebooks để download/explore dữ liệu
└── scripts/                # Script phụ trợ
```

---

## Luồng xử lý (Pipeline Flow)

```
┌─────────────────────────────────────────────────────────────────┐
│                         PREPROCESSING                            │
│  Shapefile → Clean → Generate H3 Grid (h3_grid.geojson)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PARALLEL PROCESSING                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │   DYNAMIC    │  │    STATIC    │  │     PERIODIC     │       │
│  │  (Daily)     │  │  (1 lần)     │  │  (Vệ tinh)       │       │
│  │              │  │              │  │                  │       │
│  │ • Rain       │  │ • DEM        │  │ • Sentinel NDVI  │       │
│  │ • Temp       │  │ • Landcover  │  │ • Sentinel NDWI  │       │
│  │ • Humidity   │  │ • River      │  │                  │       │
│  │ • Solar      │  │              │  │                  │       │
│  └──────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           MERGE                                  │
│  • FINAL_MERGED_DATASET.csv  (Dynamic)                          │
│  • DIM_H3_STATIC.csv         (Static)                           │
│  • PERIODIC_MERGED.csv       (Periodic)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Các loại dữ liệu

### 1. Dynamic Data (Dữ liệu động - hàng ngày)

| Dataset   | Folder           | Cột output      | Mô tả                    |
|-----------|------------------|-----------------|--------------------------|
| rain      | daily_rain       | rain_mm         | Lượng mưa (mm)           |
| temp_avg  | daily_temp_avg   | temp_c          | Nhiệt độ trung bình (°C) |
| temp_max  | daily_temp_max   | temp_max_c      | Nhiệt độ cao nhất (°C)   |
| temp_min  | daily_temp_min   | temp_min_c      | Nhiệt độ thấp nhất (°C)  |
| humidity  | daily_humid      | rh_percent      | Độ ẩm (%)                |
| solar     | daily_solar      | solar           | Bức xạ mặt trời          |

**Format file**: `{year}_{month}.tif` với mỗi band là 1 ngày trong tháng.

### 2. Static Data (Dữ liệu tĩnh)

| Dataset   | File                      | Method         | Output                                |
|-----------|---------------------------|----------------|---------------------------------------|
| dem       | DEM_DBSCL.tif             | mean           | dem_mean (độ cao trung bình)          |
| landcover | LandCover_DBSCL_2021.tif  | all_classes    | Tỷ lệ % từng loại đất                 |
| river     | River_DBSCL.tif           | min_distance   | Khoảng cách đến sông (km) + tỷ lệ nước|

**Landcover Classes:**
- 10: Trees, 20: Shrubland, 30: Grassland, 40: Cropland
- 50: Built_up, 60: Bareland, 80: Water, 90: Wetland, 95: Mangroves

### 3. Periodic Data (Dữ liệu vệ tinh - theo chu kỳ)

| Dataset       | Pattern           | Method | Mô tả                  |
|---------------|-------------------|--------|------------------------|
| sentinel_ndvi | NDVI_{date}.tif   | mean   | Chỉ số thực vật NDVI   |
| sentinel_ndwi | NDWI_{date}.tif   | mean   | Chỉ số nước NDWI       |

---

## Các hàm chính

### `preprocessing.py`

| Hàm                    | Mô tả                                                    |
|------------------------|----------------------------------------------------------|
| `run_preprocessing()`  | Orchestrator: chạy toàn bộ bước tiền xử lý               |
| `clean_shapefile()`    | Loại bỏ các đảo nhỏ khỏi shapefile                       |
| `generate_h3_grid()`   | Tạo lưới H3 từ shapefile đã clean                        |

### `processing.py`

| Hàm                            | Mô tả                                                        |
|--------------------------------|--------------------------------------------------------------|
| `extract_generic()`            | Trích xuất dữ liệu dynamic từ raster multiband               |
| `extract_static_generic()`     | Trích xuất dữ liệu static (DEM, landcover, river)            |
| `extract_periodic_generic()`   | Trích xuất dữ liệu periodic (NDVI, NDWI)                     |
| `fill_spatial_generic()`       | Fill missing bằng K-Ring neighbors (hàng xóm vành khuyên)    |
| `fill_final_nearest()`         | Fill cuối cùng bằng Nearest Neighbor (KDTree)                |
| `merge_dynamic_datasets()`     | Gộp tất cả file dynamic thành 1 file CSV                     |
| `merge_static_datasets()`      | Gộp tất cả file static thành 1 file CSV                      |
| `merge_periodic_datasets()`    | Gộp tất cả file periodic thành 1 file CSV                    |

### `utils_h3.py`

| Hàm                         | Mô tả                                              |
|-----------------------------|----------------------------------------------------|
| `load_h3_multipoints()`     | Load H3 grid và tạo sample points                  |
| `sample_multiband_robust()` | Lấy mẫu từ raster với fallback (centroid → edge)   |
| `parse_year_month()`        | Parse năm-tháng từ tên file                        |
| `index_files()`             | Index tất cả file .tif theo (year, month)          |

---

## Chi tiết các phương pháp trích xuất dữ liệu

### 1. Trích xuất dữ liệu Dynamic (`extract_generic`)

**Mục đích:** Trích xuất dữ liệu thời tiết hàng ngày (mưa, nhiệt độ, độ ẩm...) từ file raster multiband.

**Input:** File TIF với format `{year}_{month}.tif`, mỗi band = 1 ngày trong tháng.

**Thuật toán:**

```
┌─────────────────────────────────────────────────────────────┐
│  1. Index tất cả file .tif theo (year, month)               │
│  2. Với mỗi file:                                           │
│     ├── Đọc tất cả bands (31 bands = 31 ngày)               │
│     └── Với mỗi ô H3:                                       │
│         ├── Lấy mẫu tại CENTROID (tâm ô)                    │
│         ├── Nếu centroid = NoData:                          │
│         │   └── Fallback: lấy trung bình 6 MIDPOINTS (cạnh) │
│         └── Ghi vào record: (h3_index, date, value)         │
└─────────────────────────────────────────────────────────────┘
```

**Chiến lược lấy mẫu (Robust Sampling):**

```
        Ô lục giác H3
           ╱╲
          ╱  ╲
         ╱ M2 ╲
        ╱──────╲
       ╱   M1   ╲
      ╱    ●     ╲ M3      ● = Centroid (ưu tiên)
     ╱   (C)     ╲         M = Midpoint (fallback)
     ╲           ╱
      ╲   M6   ╱
       ╲──────╱
        ╲ M5 ╱
         ╲  ╱
          ╲╱
           M4

Bước 1: Lấy giá trị tại Centroid (C)
Bước 2: Nếu C = NoData → Lấy TB của 6 Midpoints (M1-M6)
```

**Output:** DataFrame với cột `[h3_index, date, {col_name}]`

---

### 2. Trích xuất dữ liệu Static (`extract_static_generic`)

**Mục đích:** Trích xuất đặc trưng địa hình tĩnh (DEM, landcover, sông) từ file raster single-band.

**3 phương pháp (method) khác nhau:**

#### Method 1: `mean` / `max` / `min` (Zonal Stats cơ bản)

**Dùng cho:** DEM, slope, elevation

```python
# Ví dụ config:
"dem": {
    "file": "DEM_DBSCL.tif",
    "method": "mean"  # hoặc "max", "min"
}
```

**Thuật toán:**
```
┌────────────────────────────────────────────────────┐
│  1. Tạo GeoDataFrame từ H3 polygons                │
│  2. Gọi rasterstats.zonal_stats()                  │
│     với stats="mean" (hoặc max/min)                │
│  3. Trả về 1 giá trị thống kê cho mỗi ô H3         │
└────────────────────────────────────────────────────┘
```

**Minh họa:**
```
┌─────────────────┐
│  Raster DEM     │      Ô H3
│  ┌───┬───┬───┐  │       ╱╲
│  │ 5 │ 6 │ 7 │  │      ╱  ╲
│  ├───┼───┼───┤  │     ╱ 5,6╲
│  │ 4 │ 5 │ 6 │──┼──▶ ╱  7,4 ╲  → mean = 5.5
│  ├───┼───┼───┤  │    ╲  5,6 ╱
│  │ 3 │ 4 │ 5 │  │     ╲    ╱
│  └───┴───┴───┘  │      ╲  ╱
└─────────────────┘       ╲╱
```

**Output:** `[h3_index, dem_mean]`

---

#### Method 2: `all_classes` (Tỷ lệ % từng class)

**Dùng cho:** Landcover, land use, soil type

```python
# Ví dụ config:
"landcover": {
    "file": "LandCover_DBSCL_2021.tif",
    "method": "all_classes",
    "class_names": {
        10: "Trees",
        40: "Cropland",
        80: "Water"
    }
}
```

**Thuật toán:**
```
┌────────────────────────────────────────────────────────────┐
│  1. Gọi zonal_stats(..., categorical=True)                 │
│     → Đếm số pixel của từng class trong mỗi ô H3           │
│                                                            │
│  2. Tính tỷ lệ %:                                          │
│     fraction = pixel_count / total_pixels                  │
│                                                            │
│  3. Dịch mã số → tên class (từ class_names dict)           │
│     Ví dụ: 40 → "Cropland"                                 │
│                                                            │
│  4. Tạo cột động: "{col_name}_{class_name}"                │
│     Ví dụ: landcover_Cropland, landcover_Water             │
└────────────────────────────────────────────────────────────┘
```

**Minh họa:**
```
┌─────────────────┐
│  Raster Class   │      Ô H3
│  ┌───┬───┬───┐  │       ╱╲
│  │40 │40 │80 │  │      ╱  ╲
│  ├───┼───┼───┤  │     ╱40,40╲
│  │40 │40 │40 │──┼──▶ ╱ 80,40╲  → Cropland: 0.67
│  ├───┼───┼───┤  │    ╲ 40,80╱    Water: 0.33
│  │40 │80 │80 │  │     ╲    ╱
│  └───┴───┴───┘  │      ╲  ╱
└─────────────────┘       ╲╱
```

**Output:** `[h3_index, landcover_Trees, landcover_Cropland, landcover_Water, ...]`

---

#### Method 3: `min_distance` (Khoảng cách đến sông)

**Dùng cho:** River proximity, distance to coast

```python
# Ví dụ config:
"river": {
    "file": "River_DBSCL.tif",  # Binary: 0=đất, 1=sông
    "method": "min_distance"
}
```

**Thuật toán:**
```
┌────────────────────────────────────────────────────────────────┐
│  BƯỚC 1: Tính tỷ lệ nước trong mỗi ô H3                        │
│  ├── zonal_stats(..., stats="mean") trên file binary (0/1)     │
│  └── mean chính là tỷ lệ % pixel = 1 (sông)                    │
│                                                                │
│  BƯỚC 2: Tìm tất cả pixel sông (giá trị = 1)                   │
│  ├── Đọc raster, lọc river_mask = (data == 1)                  │
│  └── Chuyển pixel → tọa độ thực (x, y)                         │
│                                                                │
│  BƯỚC 3: Xây KDTree từ tọa độ sông                             │
│  ├── tree = cKDTree(river_coords)                              │
│  └── KDTree cho phép tìm kiếm nhanh O(log n)                   │
│                                                                │
│  BƯỚC 4: Đo khoảng cách từ tâm H3 đến sông gần nhất            │
│  ├── h3_coords = centroid của từng ô H3                        │
│  ├── dists, _ = tree.query(h3_coords)                          │
│  └── Quy đổi: km = dists * 111.32 (nếu CRS geographic)         │
│                                                                │
│  BƯỚC 5: Logic đặc biệt                                        │
│  └── Nếu ô H3 đã có nước (fraction > 5%) → distance = 0        │
└────────────────────────────────────────────────────────────────┘
```

**Minh họa:**
```
     Raster River (0/1)              KDTree Query
    ┌───┬───┬───┬───┬───┐
    │ 0 │ 0 │ 1 │ 1 │ 0 │     Ô H3 (●)      Sông gần nhất (★)
    ├───┼───┼───┼───┼───┤         ╱╲
    │ 0 │ 0 │ 1 │ 0 │ 0 │        ╱  ╲           ★ ← pixel sông
    ├───┼───┼───┼───┼───┤       ╱    ╲         ╱
    │ 0 │ 0 │ 0 │ 0 │ 0 │      ╱  ●   ╲───────╱ distance = 2.3 km
    ├───┼───┼───┼───┼───┤      ╲ (tâm)╱
    │ 0 │ 0 │ 0 │ 0 │ 0 │       ╲    ╱
    └───┴───┴───┴───┴───┘        ╲  ╱
                                  ╲╱
```

**Output:** `[h3_index, river_proximity, river_proximity_fraction]`

---

### 3. Trích xuất dữ liệu Periodic (`extract_periodic_generic`)

**Mục đích:** Trích xuất dữ liệu vệ tinh theo chu kỳ (NDVI, NDWI từ Sentinel-2).

**Input:** Nhiều file TIF, mỗi file = 1 ngày chụp (single band).
- Format tên: `NDVI_{date}.tif` (ví dụ: `NDVI_2023-01-15.tif`)

**Thuật toán:**
```
┌────────────────────────────────────────────────────────────┐
│  1. Index files theo ngày (parse date từ filename)         │
│     ├── Regex: NDVI_(?P<date>\d{4}[-_]?\d{2}[-_]?\d{2})    │
│     └── Output: {datetime: file_path}                      │
│                                                            │
│  2. Filter theo khoảng thời gian (nếu có from/to_date)     │
│                                                            │
│  3. Với mỗi file (mỗi ngày chụp):                          │
│     ├── Dùng zonal_stats() với method (thường là "mean")   │
│     └── Ghi record: (h3_index, date, value)                │
│                                                            │
│  4. Fill missing (nếu cấu hình):                           │
│     ├── interpolate: Nội suy tuyến tính                    │
│     ├── forward: Dùng giá trị trước đó (ffill)             │
│     └── backward: Dùng giá trị sau đó (bfill)              │
└────────────────────────────────────────────────────────────┘
```

**Timeline minh họa:**
```
Dữ liệu vệ tinh (không liên tục):

    Jan 15      Feb 01      Feb 17      Mar 05
      │           │           │           │
      ▼           ▼           ▼           ▼
    ┌───┐       ┌───┐       ┌───┐       ┌───┐
    │0.6│       │0.7│       │NaN│       │0.8│  ← NDVI values
    └───┘       └───┘       └───┘       └───┘
                              │
                              ▼
                    Interpolate → 0.75
```

**Output:** `[h3_index, date, ndvi]` (hoặc ndwi)

---

### So sánh 3 loại trích xuất

| Đặc điểm        | Dynamic              | Static               | Periodic             |
|-----------------|----------------------|----------------------|----------------------|
| **Tần suất**    | Hàng ngày            | 1 lần (không đổi)    | Theo chu kỳ (~16 ngày)|
| **File format** | Multiband TIF        | Single-band TIF      | Nhiều Single-band TIF|
| **Sampling**    | Point (centroid+edge)| Zonal (toàn ô H3)    | Zonal (toàn ô H3)    |
| **Output cols** | 1 cột giá trị        | 1 hoặc nhiều cột     | 1 cột giá trị        |
| **Has date**    | Có                   | Không                | Có                   |
| **Fill method** | K-Ring + KDTree      | Không cần            | Interpolate          |

---

## Chiến lược Fill Missing Data

### Bước 1: Spatial Fill (K-Ring) - `fill_spatial_generic()`

**Mục đích:** Điền giá trị thiếu bằng trung bình các ô hàng xóm lân cận.

**Cấu hình:**
- `MAX_K = 3`: Tìm trong vành khuyên K=1, 2, 3
- `MIN_NEI = 3`: Cần tối thiểu 3 ô có dữ liệu

**Thuật toán:**
```
┌─────────────────────────────────────────────────────────────┐
│  1. Precompute K-Ring cho tất cả ô H3                       │
│     k_ring_map[h][k] = list các ô hàng xóm ở vành k         │
│                                                             │
│  2. Với mỗi ô bị thiếu (h, date):                           │
│     FOR k = 1 to MAX_K:                                     │
│       ├── Lấy danh sách hàng xóm ở vành k                   │
│       ├── Lọc những ô có dữ liệu tại ngày đó                │
│       └── Nếu >= MIN_NEI ô có data:                         │
│           └── Gán giá trị = TRUNG BÌNH                      │
└─────────────────────────────────────────────────────────────┘
```

**Minh họa K-Ring:**
```
                K=1 (6 ô)         K=2 (12 ô)         K=3 (18 ô)
                  ╱╲                ╱╲                  ╱╲
                 ╱  ╲              ╱  ╲                ╱  ╲
                ╱    ╲            ╱    ╲              ╱    ╲
               ╱  ●   ╲          ╱  ○   ╲            ╱  ◇   ╲
              ╱ ╱╲ ╲   ╲        ╱ ╱╲ ╲   ╲          ╱ ╱╲ ╲   ╲
             ╱ ╱●●╲ ╲   ╲      ╱ ╱○○╲ ╲   ╲        ╱ ╱◇◇╲ ╲   ╲
            ╱ ●╲██╱● ╲   ╲    ╱ ○╲●●╱○ ╲   ╲      ╱ ◇╲○○╱◇ ╲   ╲
             ╲ ╲╱╲╱ ╱ ╱      ╲ ╲●██●╱ ╱        ╲ ╲○●●○╱ ╱
              ╲ ●● ╱ ╱        ╲ ○╲╱╲╱○ ╱        ╲ ◇○██○◇ ╱
               ╲  ╱ ╱          ╲ ○○ ╱            ╲ ◇╲╱╲╱◇
                ╲╱              ╲  ╱              ╲ ◇◇ ╱
                                 ╲╱                ╲  ╱
                                                    ╲╱
             ██ = Ô thiếu data
             ● = Vành K=1     ○ = Vành K=2     ◇ = Vành K=3
```

---

### Bước 2: Final Fill (Nearest Neighbor) - `fill_final_nearest()`

**Mục đích:** Cứu các ô bị cô lập (đảo xa, vùng mây lớn) mà K-Ring không thể fill.

**Thuật toán:**
```
┌─────────────────────────────────────────────────────────────┐
│  1. Tách ô Tốt (có data) và ô Xấu (thiếu data)              │
│                                                             │
│  2. Xây KDTree từ tọa độ các ô Tốt                          │
│     good_coords = [cell_to_latlng(h) for h in good_ids]     │
│     tree = cKDTree(good_coords)                             │
│                                                             │
│  3. Query tìm ô Tốt gần nhất cho mỗi ô Xấu                  │
│     dists, indices = tree.query(bad_coords, k=1)            │
│                                                             │
│  4. Copy data từ ô Tốt → ô Xấu (theo từng ngày)             │
│                                                             │
│  5. Interpolate nốt nếu ô nguồn cũng thiếu vài ngày         │
└─────────────────────────────────────────────────────────────┘
```

**Minh họa:**
```
     Toàn bản đồ ĐBSCL
    ┌─────────────────────────┐
    │  ●  ●  ●  ●  ●  ●  ●   │   ● = Ô có data
    │  ●  ●  ●  ●  ●  ●  ●   │   ✗ = Ô thiếu data (đảo xa)
    │  ●  ●  ●  ●  ●  ●  ●   │
    │  ●  ●  ●  ●  ●  ●  ●   │
    │  ●  ●        ●  ●  ●   │
    │                    ✗───┼──▶ Tìm ● gần nhất = 15km
    │        (biển)          │    Copy data từ ● sang ✗
    └─────────────────────────┘
```

---

### Bước 3: Temporal Interpolate (cho Periodic) - `fill_periodic_data()`

**Mục đích:** Điền khoảng trống thời gian cho dữ liệu vệ tinh.

**Các phương pháp:**

| fill_method   | Mô tả                          | Pandas function |
|---------------|--------------------------------|-----------------|
| `none`        | Không fill                     | -               |
| `interpolate` | Nội suy tuyến tính             | `.interpolate()`|
| `forward`     | Dùng giá trị trước đó          | `.ffill()`      |
| `backward`    | Dùng giá trị sau đó            | `.bfill()`      |

**Minh họa Interpolate:**
```
Trước fill:
    Date     │ NDVI
    ─────────┼──────
    Jan 15   │ 0.60
    Jan 31   │ NaN    ← Mây che
    Feb 15   │ NaN    ← Mây che
    Mar 01   │ 0.80

Sau interpolate:
    Date     │ NDVI
    ─────────┼──────
    Jan 15   │ 0.60
    Jan 31   │ 0.67   ← Nội suy
    Feb 15   │ 0.73   ← Nội suy
    Mar 01   │ 0.80
```

---

## Cách sử dụng

### 1. Cài đặt

```bash
pip install -r requirements.txt
```

### 2. Chuẩn bị dữ liệu

Đặt dữ liệu vào thư mục `data/raw/`:

```
data/raw/
├── boundary_input.shp      # Shapefile ranh giới vùng nghiên cứu
├── daily_rain/             # Dữ liệu mưa hàng ngày
│   ├── 2023_1.tif
│   ├── 2023_2.tif
│   └── ...
├── daily_temp_avg/         # Nhiệt độ trung bình
├── dem/
│   └── DEM_DBSCL.tif
├── landcover/
│   └── LandCover_DBSCL_2021.tif
├── river/
│   └── River_DBSCL.tif
└── sentinel2_ndvi/
    ├── NDVI_2023-01-15.tif
    └── ...
```

### 3. Chạy pipeline

```bash
python main.py
```

### 4. Output

Kết quả được lưu trong `data/processed/`:

```
data/processed/
├── h3_grid.geojson              # Lưới H3
├── h3_rain_daily_filled.csv     # Dữ liệu mưa theo H3
├── h3_temp_daily_filled.csv     # Dữ liệu nhiệt độ
├── h3_dem.csv                   # DEM
├── h3_landcover.csv             # Landcover
├── h3_river.csv                 # Khoảng cách sông
├── FINAL_MERGED_DATASET.csv     # Gộp tất cả dynamic
├── DIM_H3_STATIC.csv            # Gộp tất cả static
└── PERIODIC_MERGED.csv          # Gộp tất cả periodic
```

---

## Cấu hình

### Biến môi trường (Environment Variables)

| Biến                 | Mặc định | Mô tả                           |
|----------------------|----------|---------------------------------|
| H3_RESOLUTION        | 7        | Độ phân giải lưới H3 (0-15)     |
| BUFFER_DIST          | 0        | Buffer ranh giới (meters)       |
| MIN_ISLAND_AREA_KM2  | 0        | Loại bỏ đảo nhỏ hơn (km²)       |
| ENABLE_GEE_FALLBACK  | True     | Cho phép download từ GEE        |

### Custom Dataset Specs

Tạo file JSON trong `data/raw/` để override cấu hình mặc định:
- `dataset_specs.json` - Override dynamic specs
- `static_specs.json` - Override static specs
- `periodic_specs.json` - Override periodic specs

---

## Thư viện sử dụng

| Thư viện     | Mục đích                              |
|--------------|---------------------------------------|
| h3           | Hệ thống lưới lục giác H3             |
| geopandas    | Xử lý dữ liệu vector                  |
| rasterio     | Đọc/ghi file raster (GeoTIFF)         |
| rasterstats  | Tính toán zonal statistics            |
| scipy        | KDTree cho tìm kiếm không gian        |
| pandas       | Xử lý dữ liệu tabular                 |
| numpy        | Tính toán số học                      |

---

## Hệ tọa độ (CRS)

- **EPSG:4326** (WGS84): Lưu trữ và output
- **EPSG:32648** (UTM Zone 48N): Tính toán diện tích/khoảng cách

---

## Ghi chú kỹ thuật

1. **H3 Resolution 7**: Mỗi ô có diện tích ~5.16 km², cạnh ~1.22 km
2. **Multiprocessing**: Sử dụng ProcessPoolExecutor để xử lý song song
3. **Memory optimization**: Batch sampling thay vì loop từng điểm
4. **STRtree**: Spatial index để clip H3 cells nhanh hơn
