"""Aggregations used by the dashboard, road risk search, reports and Power BI export."""
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractYear

from .constants import SEVERITY_WEIGHT, TIME_ORDER, WEEKDAYS
from .ml import approved_accidents

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _sev_counts():
    return dict(
        total=Count("id"),
        fatal=Count("id", filter=Q(severity="Fatal")),
        serious=Count("id", filter=Q(severity="Serious")),
        minor=Count("id", filter=Q(severity="Minor")),
    )


def risk_index(fatal, serious, minor):
    """Weighted severity index scaled to 0-100 (100 = every accident fatal)."""
    total = fatal + serious + minor
    if not total:
        return 0.0
    weighted = fatal * SEVERITY_WEIGHT["Fatal"] + serious * SEVERITY_WEIGHT["Serious"] + minor * SEVERITY_WEIGHT["Minor"]
    return round(weighted / (total * SEVERITY_WEIGHT["Fatal"]) * 100, 1)


def risk_level(index):
    if index >= 48:
        return "High"
    if index >= 40:
        return "Medium"
    return "Low"


def base_qs(year=None, corridor=None):
    qs = approved_accidents()
    if year:
        qs = qs.filter(date__year=year)
    if corridor:
        qs = qs.filter(corridor=corridor)
    return qs


def corridors():
    return list(approved_accidents().exclude(corridor="Unknown").order_by("corridor")
                .values_list("corridor", flat=True).distinct())


def available_years(corridor=None):
    qs = base_qs(corridor=corridor).exclude(date__isnull=True)
    return list(qs.annotate(y=ExtractYear("date")).values_list("y", flat=True).distinct().order_by("y"))


def monthly(qs):
    rows = {r["m"]: r for r in qs.exclude(date__isnull=True).annotate(m=ExtractMonth("date")).values("m").annotate(**_sev_counts())}
    return [{"month": MONTHS[m - 1], **{k: rows.get(m, {}).get(k, 0) for k in ("total", "fatal", "serious", "minor")}}
            for m in range(1, 13)]


def yearly(qs):
    return [{"year": r["y"], **{k: r[k] for k in ("total", "fatal", "serious", "minor")}}
            for r in qs.exclude(date__isnull=True).annotate(y=ExtractYear("date")).values("y").annotate(**_sev_counts()).order_by("y")]


def by_field(qs, field, order=None):
    out = []
    for r in qs.values(field).annotate(**_sev_counts()).order_by("-total"):
        out.append({"label": r[field], **{k: r[k] for k in ("total", "fatal", "serious", "minor")},
                    "risk_index": risk_index(r["fatal"], r["serious"], r["minor"])})
    if order:
        out.sort(key=lambda x: order.index(x["label"]) if x["label"] in order else 99)
    return out


def top_roads(qs, limit=10, min_total=15):
    rows = []
    for r in qs.values("road_name", "corridor").annotate(**_sev_counts()):
        if r["total"] < min_total:
            continue
        idx = risk_index(r["fatal"], r["serious"], r["minor"])
        weighted = r["fatal"] * 5 + r["serious"] * 3 + r["minor"]
        rows.append({**r, "city": r["corridor"], "risk_index": idx, "risk_level": risk_level(idx), "weighted": weighted})
    rows.sort(key=lambda x: x["weighted"], reverse=True)
    return rows[:limit]


def kpis(qs):
    c = qs.aggregate(**_sev_counts())
    return {**c, "risk_index": risk_index(c["fatal"], c["serious"], c["minor"]),
            "fatal_pct": round(c["fatal"] / c["total"] * 100, 1) if c["total"] else 0}


def dashboard_data(year=None, corridor=None):
    qs = base_qs(year, corridor)
    return {
        "kpis": kpis(qs),
        "monthly": monthly(qs),
        "yearly": yearly(base_qs(corridor=corridor)),
        "weather": by_field(qs, "weather"),
        "time_of_day": by_field(qs, "time_of_day", TIME_ORDER),
        "day_of_week": by_field(qs, "day_of_week", WEEKDAYS),
        "vehicle": by_field(qs, "vehicle_type"),
        "cause": by_field(qs, "cause"),
        "road_condition": by_field(qs, "road_condition"),
        "roads": top_roads(qs, 10),
        "severity": {"Minor": kpis(qs)["minor"], "Serious": kpis(qs)["serious"], "Fatal": kpis(qs)["fatal"]},
    }


def search_roads(query, limit=30):
    qs = approved_accidents().filter(Q(road_name__icontains=query) | Q(corridor__icontains=query))
    rows = []
    for r in qs.values("road_name", "corridor").annotate(**_sev_counts()):
        idx = risk_index(r["fatal"], r["serious"], r["minor"])
        rows.append({**r, "city": r["corridor"], "risk_index": idx, "risk_level": risk_level(idx)})
    rows.sort(key=lambda x: (x["risk_index"], x["total"]), reverse=True)
    return rows[:limit]


def road_profile(road_name):
    qs = approved_accidents().filter(road_name=road_name)
    if not qs.exists():
        return None
    k = kpis(qs)
    return {
        "road_name": road_name,
        "city": qs.values_list("corridor", flat=True).first(),
        "kpis": k,
        "risk_level": risk_level(k["risk_index"]),
        "weather": by_field(qs, "weather")[:5],
        "time_of_day": by_field(qs, "time_of_day", TIME_ORDER),
        "vehicle": by_field(qs, "vehicle_type")[:5],
        "cause": by_field(qs, "cause"),
        "yearly": yearly(qs),
    }
