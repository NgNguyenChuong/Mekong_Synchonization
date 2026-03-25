import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List
from urllib.request import Request, urlopen


BASE_WET_URL = "https://ffw.mrcmekong.org/fetchwet_new.php"
BASE_DRY_URL = "https://ffw.mrcmekong.org/fetchdry_new.php"

def _js_like_array_to_json(text: str) -> str:
	"""
	Convert a JS-like array of objects with unquoted keys to valid JSON.
	Example input: [{date_gmt:"2025-11-01",Min:1.03,1992.93:2.67}, ...]
	"""
	# Quote object keys like date_gmt, Min, 1992.93
	text = re.sub(
		r"(?<=\{|,)\s*([A-Za-z0-9_.]+)\s*:",
		lambda match: f'"{match.group(1)}":',
		text,
	)
	# Remove trailing commas before ] or } to satisfy strict JSON.
	return re.sub(r",\s*(\]|\})", r"\1", text)


def fetch_water_level(st_code: str, base_url: str) -> List[Dict[str, Any]]:
	"""
	Fetch water level data for a station code from MRC FFW endpoint.
	Returns a list of dicts.
	"""
	url = f"{base_url}?StCode={st_code}"
	req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
	with urlopen(req, timeout=30) as response:
		raw = response.read().decode("utf-8").lstrip("\ufeff").strip()

	if raw.endswith(";"):
		raw = raw[:-1].strip()

	if not raw:
		return []

	json_text = _js_like_array_to_json(raw)
	try:
		return json.loads(json_text)
	except json.JSONDecodeError as exc:
		# Add context to help diagnose upstream format changes.
		raise ValueError("Unexpected response format from MRC endpoint") from exc


def _infer_output_name(st_code: str) -> str:
	stamp = datetime.now().strftime("%Y%m%d")
	return f"water_level_{st_code}_{stamp}.csv"


def _infer_long_name(out_path: str) -> str:
	if out_path.lower().endswith(".csv"):
		return out_path[:-4] + "_long.csv"
	return out_path + "_long.csv"


def _split_year_columns(data: List[Dict[str, Any]]) -> Dict[str, Any]:
	year_re = re.compile(r"^\d{4}(\.\d{2})?$")
	cols = {k for row in data for k in row.keys()}
	year_cols = sorted([c for c in cols if year_re.match(c)])
	base_cols = sorted([c for c in cols if c not in year_cols])
	return {"year_cols": year_cols, "base_cols": base_cols}


def _to_long_rows(data: List[Dict[str, Any]], season: str) -> List[Dict[str, Any]]:
	parts = _split_year_columns(data)
	rows: List[Dict[str, Any]] = []
	for row in data:
		base = {k: row.get(k, "") for k in parts["base_cols"]}
		for year_col in parts["year_cols"]:
			year_value = row.get(year_col, "")
			try:
				year = int(year_col.split(".")[0])
			except ValueError:
				year = year_col
			rows.append({**base, "year": year, "value": year_value, "season": season})
	return rows


def _combine_seasons(st_code: str) -> List[Dict[str, Any]]:
	data_wet = fetch_water_level(st_code, BASE_WET_URL)
	data_dry = fetch_water_level(st_code, BASE_DRY_URL)
	rows = []
	if data_wet:
		rows.extend(_to_long_rows(data_wet, "wet"))
	if data_dry:
		rows.extend(_to_long_rows(data_dry, "dry"))
	return rows


def _to_dd_mm_yy_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	formatted: List[Dict[str, Any]] = []
	for row in rows:
		date_gmt = str(row.get("date_gmt", ""))
		value = row.get("value", "")
		try:
			date_parts = datetime.strptime(date_gmt, "%Y-%m-%d")
			dd_mm = date_parts.strftime("%d-%m")
		except ValueError:
			dd_mm = ""

		year = row.get("year", "")
		try:
			yy = f"{int(year)}"
		except (TypeError, ValueError):
			yy = ""

		formatted.append({"dd-mm-yy": f"{dd_mm}-{yy}", "value": value})
	return formatted


def _sort_rows_by_date(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	def sort_key(row: Dict[str, Any]) -> Any:
		date_text = str(row.get("dd-mm-yy", "")).strip()
		try:
			return (0, datetime.strptime(date_text, "%d-%m-%Y"))
		except ValueError:
			# Keep malformed date rows at the end while preserving deterministic order.
			return (1, date_text)

	return sorted(rows, key=sort_key)


def main() -> int:
	parser = argparse.ArgumentParser(description="Fetch MRC water level data.")
	parser.add_argument("--st-code", default="CDO", help="Station code, e.g. CDO")
	parser.add_argument("--out", default=None, help="Output CSV path")
	args = parser.parse_args()

	long_rows = _combine_seasons(args.st_code)
	if not long_rows:
		print("No data returned.")
		return 0

	formatted_rows = _to_dd_mm_yy_rows(long_rows)
	if not formatted_rows:
		print("No formatted data returned.")
		return 0

	formatted_rows = _sort_rows_by_date(formatted_rows)

	out_path = args.out or _infer_output_name(args.st_code)
	try:
		import pandas as pd  # optional dependency
	except ImportError:
		pd = None

	if pd is None:
		# Minimal CSV writer if pandas is unavailable.
		keys = ["dd-mm-yy", "value"]
		with open(out_path, "w", encoding="utf-8") as f:
			f.write(",".join(keys) + "\n")
			for row in formatted_rows:
				f.write(",".join(str(row.get(k, "")) for k in keys) + "\n")
	else:
		pd.DataFrame(formatted_rows).to_csv(out_path, index=False)

	print(f"Saved {len(formatted_rows)} rows to {out_path}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
