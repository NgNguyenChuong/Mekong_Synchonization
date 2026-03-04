import pandas as pd

df = pd.read_csv("water_level_CDO_20260304.csv")

if "dd-mm-yy" in df.columns:
	ddmm = pd.to_datetime(df["dd-mm-yy"], format="%d-%m-%Y", errors="coerce")
	df = df.assign(_sort_date=ddmm).sort_values(["_sort_date"], ascending=[True]).drop(columns=["_sort_date"])
elif "yy" in df.columns:
	df["yy"] = pd.to_numeric(df["yy"], errors="coerce")
	df = df.sort_values(["yy"], ascending=[True])
elif "year" in df.columns:
	if "date_gmt" in df.columns:
		df["date_gmt"] = pd.to_datetime(df["date_gmt"], errors="coerce")
		df = df.sort_values(["year", "date_gmt"], ascending=[True, True])
	else:
		df = df.sort_values(["year"], ascending=[True])

print(df.to_string(index=False))