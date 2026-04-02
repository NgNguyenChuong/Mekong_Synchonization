elif method == "min_distance":
    print(f"   🌊 Đang tính toán (HYBRID) khoảng cách sông + tỷ lệ + presence...")

    # -------------------------------------------------
    # 1. TÍNH TỶ LỆ NƯỚC (fraction)
    # -------------------------------------------------
    water_stats = zonal_stats(gdf, file_path, stats="mean")
    water_fractions = np.array([
        s['mean'] if s['mean'] is not None else 0.0 
        for s in water_stats
    ])

    # -------------------------------------------------
    # 2. PRESENCE (có sông hay không)
    # -------------------------------------------------
    river_presence = water_fractions > 0   # chỉ cần có pixel là True

    # -------------------------------------------------
    # 3. CHUẨN BỊ KDTree
    # -------------------------------------------------
    with rasterio.open(file_path) as src:
        data = src.read(1)
        nodata = src.nodata

        if nodata is not None:
            river_mask = (data == 1) & (data != nodata)
        else:
            river_mask = (data == 1)

        rows, cols = np.where(river_mask)

        if len(rows) == 0:
            print("   ⚠️ Không có pixel sông.")
            vals = np.full(len(h3_ids), np.nan)

        else:
            # Tọa độ pixel sông
            xs, ys = rasterio.transform.xy(src.transform, rows, cols)
            river_coords = np.column_stack((xs, ys))
            tree = cKDTree(river_coords)

            # Tọa độ centroid H3
            centroids = gdf.geometry.centroid
            h3_coords = np.column_stack((centroids.x, centroids.y))

            # Query khoảng cách
            dists, _ = tree.query(h3_coords)

            # Convert sang km
            if src.crs and src.crs.is_geographic:
                vals = dists * 111.32
            else:
                vals = dists / 1000.0

            # -------------------------------------------------
            # 4. HYBRID LOGIC
            # Nếu có sông trong ô → distance = 0
            # -------------------------------------------------
            vals = np.where(river_presence, 0.0, vals)

    print(f"   ✅ Xong! (Ô có sông: {river_presence.sum()}/{len(h3_ids)})")

    # -------------------------------------------------
    # 5. OUTPUT 3 FEATURE
    # -------------------------------------------------
    return pd.DataFrame({
        "h3_index": h3_ids,
        col_name: vals,                                   # distance (km)
        f"{col_name}_fraction": water_fractions,           # fraction
        f"{col_name}_presence": river_presence.astype(int) # 0/1
    })