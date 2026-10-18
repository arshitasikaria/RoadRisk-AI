"""CSV ingestion and validation for accident datasets."""
import pandas as pd

from .models import Accident

REQUIRED = ["road_name", "weather", "time_of_day", "vehicle_type", "severity"]
OPTIONAL_DEFAULTS = {"corridor": "Unknown", "area_type": "Unknown", "road_type": "Unknown",
                     "road_condition": "Unknown", "day_of_week": "Unknown", "cause": "Unknown"}
SEVERITY_MAP = {
    "fatal": "Fatal", "killed": "Fatal", "death": "Fatal", "1": "Fatal",
    "serious": "Serious", "grievous": "Serious", "grievous injury": "Serious", "severe": "Serious", "2": "Serious",
    "minor": "Minor", "slight": "Minor", "simple injury": "Minor", "minor injury": "Minor",
    "non-injury": "Minor", "no injury": "Minor", "3": "Minor", "4": "Minor",
}
MAX_ROWS = 300_000


class DatasetError(Exception):
    pass


def ingest_csv(file_obj, dataset):
    """Validate a CSV file and store its rows as Accident records.
    Returns (stored, skipped_invalid, duplicates_removed)."""
    try:
        df = pd.read_csv(file_obj)
    except Exception as exc:
        raise DatasetError(f"Could not read the file as CSV: {exc}")

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DatasetError("Missing required column(s): " + ", ".join(missing) + ". Required columns: " + ", ".join(REQUIRED)
                           + ". Optional: date, " + ", ".join(OPTIONAL_DEFAULTS) + ".")
    if len(df) > MAX_ROWS:
        raise DatasetError(f"File has {len(df)} rows; the limit is {MAX_ROWS}.")

    total = len(df)
    for col, default in OPTIONAL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date if "date" in df.columns else None

    text_cols = ["road_name", "weather", "time_of_day", "vehicle_type"] + list(OPTIONAL_DEFAULTS)
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()
    df["severity"] = df["severity"].astype("string").str.strip().str.lower().map(SEVERITY_MAP)
    df = df.dropna(subset=["road_name", "weather", "time_of_day", "vehicle_type", "severity"])
    skipped = total - len(df)
    for col, default in OPTIONAL_DEFAULTS.items():
        df[col] = df[col].fillna(default)
    before = len(df)
    df = df.drop_duplicates()                     # identical records would leak between train and test
    duplicates = before - len(df)
    if df.empty:
        raise DatasetError("No valid rows found after validation (check severity values: Fatal / Serious / Minor).")

    objs = []
    for r in df.itertuples(index=False):
        d = r.date if (r.date is not None and not pd.isna(r.date)) else None
        objs.append(Accident(
            dataset=dataset, date=d, road_name=str(r.road_name)[:150], corridor=str(r.corridor)[:80],
            area_type=str(r.area_type)[:30], road_type=str(r.road_type)[:40], road_condition=str(r.road_condition)[:40],
            weather=str(r.weather)[:30], time_of_day=str(r.time_of_day)[:20], day_of_week=str(r.day_of_week)[:12],
            vehicle_type=str(r.vehicle_type)[:40], cause=str(r.cause)[:60], severity=str(r.severity)))
    Accident.objects.bulk_create(objs, batch_size=1000)
    return len(objs), skipped, duplicates
