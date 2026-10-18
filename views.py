import csv
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import analytics, ml, reports
from .constants import DATA_CREDIT, DEFAULT_CORRIDOR, FEATURE_LABELS, SEVERITY_NOTE
from .forms import DatasetUploadForm, PredictForm, RegisterForm
from .ingest import DatasetError, ingest_csv
from .models import Accident, Dataset, MLModel, Prediction, Recommendation, RegionStat, Report, User
from .permissions import role_required
from .recommendations import build_recommendations


def _corridor_param(request):
    """Dashboard corridor filter: default = Pune-Solapur, 'all' = every corridor."""
    avail = analytics.corridors()
    value = request.GET.get("corridor")
    if value is None:
        return DEFAULT_CORRIDOR if DEFAULT_CORRIDOR in avail else None
    return None if value in ("", "all") else value


# ---------- public pages ----------
def home(request):
    qs = analytics.base_qs()
    ctx = {"kpis": analytics.kpis(qs), "model_ready": ml.model_ready(), "corridors": analytics.corridors(),
           "best_model": MLModel.objects.filter(is_best=True).first(), "credit": DATA_CREDIT}
    return render(request, "core/home.html", ctx)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to RoadRisk AI! Your account has been created.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


def road_search(request):
    q = request.GET.get("q", "").strip()
    road = request.GET.get("road", "").strip()
    results = analytics.search_roads(q) if q else []
    profile = analytics.road_profile(road) if road else None
    top = analytics.top_roads(analytics.base_qs(), 8) if not q and not road else []
    return render(request, "core/search.html", {"q": q, "results": results, "profile": profile, "top": top})


def states(request):
    kind = request.GET.get("type", "state")
    if kind not in ("state", "ut", "city"):
        kind = "state"
    sort = request.GET.get("sort", "died")
    rows = list(RegionStat.objects.filter(category=kind))
    keys = {"died": lambda r: r.road_died, "cases": lambda r: r.road_cases,
            "rate": lambda r: r.deaths_per_100, "name": lambda r: r.name}
    rows.sort(key=keys.get(sort, keys["died"]), reverse=(sort != "name"))
    big = [r for r in rows if r.road_cases >= 100]
    top_died = sorted(rows, key=lambda r: r.road_died, reverse=True)[:10]
    top_rate = sorted(big, key=lambda r: r.deaths_per_100, reverse=True)[:10]
    nation = RegionStat.objects.filter(category__in=["state", "ut"])
    cases = sum(r.road_cases for r in nation)
    died = sum(r.road_died for r in nation)
    injured = sum(r.road_injured for r in nation)
    chart = {"died": {"labels": [r.name for r in top_died], "values": [r.road_died for r in top_died]},
             "rate": {"labels": [r.name for r in top_rate], "values": [r.deaths_per_100 for r in top_rate]}}
    return render(request, "core/states.html", {
        "rows": rows, "kind": kind, "sort": sort, "chart": chart,
        "kpi": {"cases": cases, "injured": injured, "died": died, "rate": round(died / cases * 100, 1) if cases else 0},
        "loaded": RegionStat.objects.exists()})


# ---------- prediction ----------
@login_required
def predict_view(request):
    if not ml.model_ready():
        return render(request, "core/no_model.html")
    form = PredictForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cond = {f: form.cleaned_data[f] for f in form.model_features}
        label, probs, model_name = ml.predict(cond)
        pred = Prediction.objects.create(
            user=request.user, road_name=form.cleaned_data["road_name"], conditions=cond, predicted_severity=label,
            confidence=probs[label], probabilities=probs, model_used=model_name)
        for text in build_recommendations(label, cond):
            Recommendation.objects.create(prediction=pred, suggestion_text=text)
        return redirect("prediction_detail", pk=pred.pk)
    roads = list(Accident.objects.order_by().values_list("road_name", flat=True).distinct()[:400])
    return render(request, "core/predict.html", {"form": form, "roads": roads, "best_model": MLModel.objects.filter(is_best=True).first()})


def _own_prediction(request, pk):
    pred = get_object_or_404(Prediction, pk=pk)
    if pred.user_id != request.user.id and not request.user.is_analyst_role:
        raise Http404
    return pred


@login_required
def prediction_detail(request, pk):
    pred = _own_prediction(request, pk)
    probs = [(k, round(v * 100, 1)) for k, v in pred.probabilities.items()]
    cond_rows = [(FEATURE_LABELS.get(k, k), v) for k, v in pred.conditions.items()]
    return render(request, "core/prediction_detail.html", {
        "p": pred, "probs": probs, "recs": pred.recommendations.all(), "cond_rows": cond_rows,
        "note": SEVERITY_NOTE.get(pred.predicted_severity, "")})


@login_required
def history(request):
    qs = Prediction.objects.select_related("user")
    if not request.user.is_analyst_role:
        qs = qs.filter(user=request.user)
    return render(request, "core/history.html", {"predictions": qs[:200], "all_users": request.user.is_analyst_role})


# ---------- dashboard ----------
@login_required
def dashboard(request):
    corridor = _corridor_param(request)
    year = request.GET.get("year") or ""
    return render(request, "core/dashboard.html", {
        "corridors": analytics.corridors(), "corridor": corridor or "", "years": analytics.available_years(corridor), "year": year,
        "datasets": Dataset.objects.filter(status="approved"), "credit": DATA_CREDIT})


@login_required
def dashboard_data(request):
    year = request.GET.get("year") or None
    return JsonResponse(analytics.dashboard_data(int(year) if year else None, _corridor_param(request)))


# ---------- reports ----------
@login_required
def report_pdf(request, pk):
    pred = _own_prediction(request, pk)
    report = getattr(pred, "report", None)
    if report is None:
        report = Report(prediction=pred)
        report.file.save(f"prediction_{pred.pk}.pdf", ContentFile(reports.prediction_pdf(pred)))
        report.save()
    return FileResponse(report.file.open("rb"), as_attachment=True, filename=f"RoadRisk_Prediction_{pred.pk}.pdf",
                        content_type="application/pdf")


@login_required
def report_excel(request, pk):
    pred = _own_prediction(request, pk)
    resp = HttpResponse(reports.prediction_excel(pred), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="RoadRisk_Prediction_{pred.pk}.xlsx"'
    return resp


@role_required("analyst")
def analytics_report(request):
    year = request.GET.get("year") or None
    resp = HttpResponse(reports.analytics_excel(int(year) if year else None, _corridor_param(request)),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="RoadRisk_Analytics_Report.xlsx"'
    return resp


# ---------- admin: datasets ----------
@role_required("admin")
def dataset_list(request):
    form = DatasetUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        ds = Dataset.objects.create(name=form.cleaned_data["name"], uploaded_by=request.user,
                                    status="approved" if form.cleaned_data["approve"] else "pending")
        f = form.cleaned_data["file"]
        try:
            stored, skipped, dups = ingest_csv(f, ds)
        except DatasetError as exc:
            ds.delete()
            messages.error(request, str(exc))
        else:
            f.seek(0)
            ds.file.save(f.name, f, save=False)
            ds.rows_count, ds.duplicates_removed = stored, dups
            ds.save()
            extra = []
            if skipped:
                extra.append(f"{skipped} invalid rows skipped")
            if dups:
                extra.append(f"{dups} duplicate rows removed")
            messages.success(request, f"Stored {stored} records" + (f" ({', '.join(extra)})" if extra else "")
                             + ". Train the models again to use the new data.")
            return redirect("dataset_list")
    return render(request, "core/datasets.html", {"form": form, "datasets": Dataset.objects.all()})


@require_POST
@role_required("admin")
def dataset_action(request, pk, action):
    ds = get_object_or_404(Dataset, pk=pk)
    if action == "approve":
        ds.status = "approved"
        ds.save()
        messages.success(request, f"'{ds.name}' approved.")
    elif action == "delete":
        ds.delete()
        messages.success(request, "Dataset deleted.")
    return redirect("dataset_list")


# ---------- admin: ML ----------
@role_required("admin")
def train_view(request):
    if request.method == "POST":
        try:
            best, _ = ml.train_models(request.user)
            messages.success(request, f"Training complete. Best model: {best}. It is now used for live predictions.")
        except ml.TrainingError as exc:
            messages.error(request, str(exc))
        return redirect("train")
    latest_run = MLModel.objects.order_by("-trained_at").values_list("run_id", flat=True).first()
    current = list(MLModel.objects.filter(run_id=latest_run).order_by("-f1_score")) if latest_run else []
    best = next((m for m in current if m.is_best), None)
    conf = None
    if best:
        d = best.details
        conf = {"labels": d["labels"], "rows": list(zip(d["labels"], d["confusion"]))}
    return render(request, "core/train.html", {
        "current": current, "best": best, "conf": conf,
        "importance": json.dumps(best.details.get("importance", {})) if best else "{}",
        "history": MLModel.objects.all()[:20],
        "n_records": ml.approved_accidents().count(), "xgb": ml.XGBClassifier is not None,
        "feature_labels": json.dumps(FEATURE_LABELS)})


# ---------- admin: users ----------
@role_required("admin")
def user_list(request):
    if request.method == "POST":
        user = get_object_or_404(User, pk=request.POST.get("user_id"))
        role = request.POST.get("role")
        if user == request.user:
            messages.error(request, "You cannot change your own role.")
        elif role in dict(User.ROLE_CHOICES):
            user.role = role
            user.save()
            messages.success(request, f"{user.username} is now {user.get_role_display()}.")
        return redirect("user_list")
    return render(request, "core/users.html", {"users": User.objects.order_by("username"), "roles": User.ROLE_CHOICES})


# ---------- admin: Power BI ----------
@role_required("admin")
def powerbi(request):
    return render(request, "core/powerbi.html", {"embed_url": settings.POWERBI_EMBED_URL, "n": ml.approved_accidents().count()})


@role_required("admin")
def powerbi_export(request):
    cols = ["date", "year", "month", "road_name", "corridor", "area_type", "road_type", "road_condition", "weather",
            "time_of_day", "day_of_week", "vehicle_type", "cause", "severity", "severity_weight"]
    weight = {"Fatal": 5, "Serious": 3, "Minor": 1}

    class Echo:
        def write(self, value):
            return value

    writer = csv.writer(Echo())

    def rows():
        yield writer.writerow(cols)
        for a in ml.approved_accidents().order_by("id").iterator(chunk_size=2000):
            yield writer.writerow([a.date or "", a.date.year if a.date else "", a.date.month if a.date else "", a.road_name,
                                   a.corridor, a.area_type, a.road_type, a.road_condition, a.weather, a.time_of_day,
                                   a.day_of_week, a.vehicle_type, a.cause, a.severity, weight.get(a.severity, 1)])

    resp = StreamingHttpResponse(rows(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="roadrisk_powerbi_export.csv"'
    return resp
