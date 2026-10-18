"""Convert the raw NHAI highway accident file (Zenodo 10.5281/zenodo.16946653) into the
format used by RoadRisk AI.

    python tools/prepare_nhai_dataset.py

Steps: decode the numeric codes (code tables from the authors' paper in F1000Research 2023,
12:494, Table 1), remove exact duplicate rows (the raw file lists every record twice),
derive the weekday from the date, assign each record to a highway corridor, build 10-km road stretches from the chainage,
and group the 4 injury classes into Fatal / Serious / Minor.
Source: Khanum, Kulkarni, Garg & Faheem (2025), Zenodo doi:10.5281/zenodo.16946653, licence CC BY 4.0.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_data" / "ETP_4_New_Data_Accidents.csv"
OUT = ROOT / "sample_data" / "nhai_highway_accidents.csv"

SEVERITY = {1: "Fatal", 2: "Serious", 3: "Minor", 4: "Minor"}   # 2 = Grievous, 4 = No injury (grouped with Minor)
AREA = {1: "Urban", 2: "Rural"}
ROAD_TYPE = {1: "Single lane", 2: "Two lanes", 3: "Three+ lanes (undivided)", 4: "Four+ lanes (divided)"}
ROAD_COND = {1: "Straight road", 2: "Slight curve", 3: "Sharp curve", 4: "Flat road", 5: "Gentle incline",
             6: "Steep incline", 7: "Hump", 8: "Dip"}
WEATHER = {1: "Fine", 2: "Mist/Fog", 3: "Cloudy", 4: "Light rain", 5: "Heavy rain", 6: "Hail/Snow", 7: "Hail/Snow",
           8: "Strong wind", 9: "Dust storm", 10: "Very hot", 11: "Very cold", 12: "Other extreme weather"}
VEHICLE = {1: "Car/Jeep/Van", 2: "SUV", 3: "Bus", 4: "Mini bus", 5: "Truck", 6: "Two-wheeler", 7: "Three-wheeler",
           8: "Cycle", 9: "Pedestrian", 10: "Tractor", 11: "Unknown", 12: "Animal", 13: "Object", 14: "LCV", 15: "MAV"}
CAUSE = {1: "Drunken driving", 2: "Overspeeding", 3: "Vehicle out of control"}   # codes 4-8 grouped below
CAUSE_OTHER = "Other (driver / vehicle / road fault)"


def corridor(row):
    c, y = row["chain"], row["year"]
    if y >= 2022:
        return "Nagpur & Chengapally-Walayar (2022-23)", "Nagpur/Chengapally"
    if 144.4 <= c <= 249.0:
        return "Pune-Solapur (NH-9)", "Pune-Solapur NH-9"
    if 398.24 <= c <= 521.12:
        return "Barwa-Adda-Panagarh (NH-2)", "Barwa-Panagarh NH-2"
    return None, None


def main():
    raw = pd.read_csv(RAW)
    raw.columns = ["date", "dow", "time", "area", "chain", "side", "sev", "cause", "road", "cond", "weather", "v1", "v2"]
    n_raw = len(raw)
    df = raw.drop_duplicates().copy()
    df["d"] = pd.to_datetime(df["date"], dayfirst=True)
    df["year"] = df["d"].dt.year
    seg = df.apply(corridor, axis=1, result_type="expand")
    df["corridor"], df["short"] = seg[0], seg[1]
    df = df[df["year"] >= 2010].dropna(subset=["corridor"]).copy()   # drops 2 stray 2003 records

    hour = pd.to_datetime(df["time"], format="%H:%M").dt.hour
    df["time_of_day"] = np.select([hour < 5, hour < 12, hour < 17, hour < 21], ["Night", "Morning", "Afternoon", "Evening"], "Night")
    # The raw Day_of_Week code is inconsistent (Monday-first in older records, Sunday-first in 2022-23),
    # so the weekday is derived from the date itself, which is reliable (dd/mm/yyyy).
    df["weekday"] = df["d"].dt.day_name()
    lo = (df["chain"] // 10 * 10).astype(int)
    out = pd.DataFrame({
        "date": df["d"].dt.strftime("%Y-%m-%d"),
        "road_name": df["short"] + " km " + lo.astype(str) + "-" + (lo + 10).astype(str),
        "corridor": df["corridor"],
        "area_type": df["area"].map(AREA),
        "road_type": df["road"].map(ROAD_TYPE),
        "road_condition": df["cond"].map(ROAD_COND),
        "weather": df["weather"].map(WEATHER),
        "time_of_day": df["time_of_day"],
        "day_of_week": df["weekday"],
        "vehicle_type": df["v1"].map(VEHICLE),
        "cause": df["cause"].map(CAUSE).fillna(CAUSE_OTHER),
        "severity": df["sev"].map(SEVERITY),
    }).dropna()
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv(OUT, index=False)
    print(f"raw rows {n_raw} -> unique {len(raw.drop_duplicates())} -> kept {len(out)}")
    print(out["corridor"].value_counts().to_dict())
    print(out["severity"].value_counts().to_dict())


if __name__ == "__main__":
    main()
