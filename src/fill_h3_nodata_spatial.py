# ============================================================
# FILL H3 NODATA BẰNG SPATIAL K-RING (H3 v4.x)
# ============================================================

import os
import pandas as pd
import h3

from config import DATA_OUT

# ============================================================
# CONFIG
# ============================================================

IN_CSV  = os.path.join(DATA_OUT, "h3_solar_daily.csv")
OUT_CSV = os.path.join(DATA_OUT, "h3_solar_daily_filled_spatial.csv")

VALUE_COL = "solar"  # Cột giá trị cần fill NoData
MAX_K     = 3        # mở rộng tối đa k-ring
MIN_NEI   = 3        # số neighbor hợp lệ tối thiểu

# ============================================================
# LOAD DATA
# ============================================================

print("📥 Load CSV...")
df = pd.read_csv(IN_CSV, parse_dates=["date"])

h3_ids = df["h3_index"].unique()
dates  = df["date"].unique()

print(f"🔢 Cells: {len(h3_ids)} | Dates: {len(dates)}")

# ============================================================
# PRECOMPUTE K-RING (GRID_DISK)
# ============================================================

print("🧠 Precompute grid_disk neighbors...")
k_ring_map = {
    h: {
        k: list(h3.grid_disk(h, k))
        for k in range(1, MAX_K + 1)
    }
    for h in h3_ids
}

# ============================================================
# INDEX DATA
# ============================================================

value_map = {
    (r.h3_index, r.date): getattr(r, VALUE_COL)
    for r in df.itertuples(index=False)
}


# ============================================================
# SPATIAL FILL
# ============================================================

filled = 0
print("🧩 Spatial filling NoData...")

for date in dates:
    for h in h3_ids:
        key = (h, date)

        if pd.notna(value_map[key]):
            continue

        for k in range(1, MAX_K + 1):
            neighs = k_ring_map[h][k]

            vals = [
                value_map[(n, date)]
                for n in neighs
                if (n, date) in value_map and pd.notna(value_map[(n, date)])
            ]

            if len(vals) >= MIN_NEI:
                value_map[key] = sum(vals) / len(vals)
                filled += 1
                break

# ============================================================
# WRITE OUTPUT
# ============================================================

print("💾 Write output CSV...")
df[VALUE_COL] = [
    value_map[(r.h3_index, r.date)]
    for r in df.itertuples()
]

df.to_csv(OUT_CSV, index=False)

# ============================================================
# REPORT
# ============================================================

remain = df[VALUE_COL].isna().sum()

print("\n✅ HOÀN TẤT")
print(f"📄 Output: {OUT_CSV}")
print(f"🧩 Filled values: {filled}")
print(f"⚠️  Remaining NoData: {remain}")
