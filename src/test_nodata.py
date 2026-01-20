import rasterio
import matplotlib.pyplot as plt
import numpy as np

TIF_PATH = "../data/raw/daily_temp/NhietDo_2022_1.tif"

with rasterio.open(TIF_PATH) as ds:
    band1 = ds.read(1)
    nodata = ds.nodata

nodata_mask = band1 == nodata

plt.figure(figsize=(8, 6))
plt.imshow(nodata_mask, cmap="Reds")
plt.title("NoData mask – Band 1 (Day 1)")
plt.colorbar(label="NoData (True = đỏ)")
plt.xlabel("Pixel X")
plt.ylabel("Pixel Y")
plt.tight_layout()
plt.show()
