# Mô tả quá trình tìm khoảng cách từ một ô H3 tới sông

Quá trình này được dùng để tạo feature `river_proximity` cho mỗi ô H3 từ raster sông `River_DBSCL.tif`.

## Mục tiêu

Với mỗi ô H3, cần xác định:
- Khoảng cách từ centroid của ô tới sông gần nhất
- Tỷ lệ pixel nước nằm trong ô H3

## Dữ liệu đầu vào

- Lưới H3 ở dạng polygon
- Raster sông `River_DBSCL.tif`
- CRS của lưới H3: `EPSG:4326`

## Các bước xử lý

### 1. Tạo GeoDataFrame từ lưới H3

Mỗi ô H3 được đưa vào `GeoDataFrame` để có thể thực hiện phép tính không gian.

### 2. Tính tỷ lệ nước trong từng ô H3

Code dùng:

```python
water_stats = zonal_stats(gdf, file_path, stats="mean")
```

Vì raster sông được mã hóa bằng `0` và `1`, nên `mean` chính là tỷ lệ nước trong ô H3.

Kết quả được lưu vào cột:
- `river_proximity_fraction`

### 3. Xác định các pixel sông trong raster

Raster được đọc bằng `rasterio` và tạo mặt nạ:

```python
river_mask = (data == 1)
```

Sau đó lấy toàn bộ vị trí pixel sông bằng `np.where(river_mask)`.

### 4. Chuyển pixel sông thành tọa độ thực

Các pixel sông được đổi từ chỉ số hàng/cột sang tọa độ bằng:

```python
xs, ys = rasterio.transform.xy(src.transform, rows, cols)
```

Kết quả là tập tọa độ của các pixel sông trong không gian.

### 5. Xây cây tìm kiếm gần nhất bằng KDTree

Tập tọa độ pixel sông được đưa vào `cKDTree` để tìm nhanh điểm gần nhất với mỗi ô H3.

### 6. Lấy centroid của từng ô H3

Với mỗi polygon H3, code lấy centroid làm điểm đại diện để đo khoảng cách đến sông.

### 7. Tính khoảng cách tới sông gần nhất

Với centroid của mỗi ô H3:
- query `cKDTree`
- lấy khoảng cách tới pixel sông gần nhất
- quy đổi sang km

Nếu CRS là hệ địa lý thì dùng hệ số xấp xỉ `111.32` để đổi từ độ sang km. Nếu CRS là hệ phẳng thì chia cho `1000`.

### 8. Ép khoảng cách bằng 0 nếu ô có nước

Nếu ô H3 có tỷ lệ nước lớn hơn ngưỡng `0.05`, khoảng cách được gán bằng `0.0`.

## Đầu ra

Hàm trả về một DataFrame gồm:
- `h3_index`: mã ô H3
- `river_proximity`: khoảng cách đến sông gần nhất, đơn vị km
- `river_proximity_fraction`: tỷ lệ pixel nước trong ô

## Ý nghĩa

Giá trị `river_proximity` cho biết ô H3 đó nằm xa hay gần sông. Giá trị `0` thường có nghĩa là ô đã chứa nước hoặc nằm trực tiếp trên vùng sông.

## Tóm tắt ngắn

Cách tính khoảng cách từ ô H3 tới sông là:
1. Lấy centroid của ô H3
2. Tìm pixel sông gần nhất trong raster
3. Tính khoảng cách gần nhất bằng `cKDTree`
4. Quy đổi sang km
5. Gán `0` nếu ô có nước bên trong
