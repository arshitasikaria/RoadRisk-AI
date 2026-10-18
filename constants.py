"""Shared constants: severity classes, model features and display labels."""

SEVERITIES = ["Minor", "Serious", "Fatal"]
SEVERITY_NOTE = {
    "Minor": "Minor injury or no injury",
    "Serious": "Grievous (serious) injury",
    "Fatal": "At least one person died",
}

# Candidate model features, in display order. A feature is only used for training when the
# data contains at least two different known values for it (so any uploaded dataset works).
FEATURES = ["corridor", "area_type", "road_type", "road_condition", "weather",
            "time_of_day", "day_of_week", "vehicle_type", "cause"]

FEATURE_LABELS = {
    "corridor": "Highway corridor",
    "area_type": "Area type",
    "road_type": "Carriageway type",
    "road_condition": "Road condition",
    "weather": "Weather",
    "time_of_day": "Time of day",
    "day_of_week": "Day of week",
    "vehicle_type": "Vehicle type",
    "cause": "Contributing cause",
}

DEFAULT_CORRIDOR = "Pune-Solapur (NH-9)"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_ORDER = ["Morning", "Afternoon", "Evening", "Night"]

# Weights used for the road risk index (a Fatal accident counts most)
SEVERITY_WEIGHT = {"Fatal": 5, "Serious": 3, "Minor": 1}

DATA_CREDIT = ("Accident data: Khanum, Kulkarni, Garg & Faheem (2025), NHAI highway accident data, Zenodo "
               "doi:10.5281/zenodo.16946653 (CC BY 4.0). State statistics: NCRB, ADSI Table 1A.2.")
