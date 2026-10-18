"""Machine learning engine: preprocessing, training and comparison of Random Forest and XGBoost,
evaluation (hold-out + cross-validation), model persistence and live prediction."""
import uuid

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.db.models import Q
from sklearn.base import clone
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder

from .constants import FEATURES, SEVERITIES
from .models import Accident, MLModel

try:
    from xgboost import XGBClassifier
except Exception:  # xgboost not installed -> only Random Forest is trained
    XGBClassifier = None

MODEL_FILE = "best_model.joblib"
_cache = {"bundle": None, "mtime": None}


class TrainingError(Exception):
    pass


def approved_accidents():
    return Accident.objects.filter(Q(dataset__isnull=True) | Q(dataset__status="approved"))


def _model_path():
    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    return settings.MODEL_DIR / MODEL_FILE


def usable_features(df):
    """Features that have at least two known (non 'Unknown') values in the data."""
    return [f for f in FEATURES if f in df and df.loc[df[f] != "Unknown", f].nunique() >= 2]


def _aggregate_importance(model, columns, features):
    imp = getattr(model, "feature_importances_", None)
    if imp is None:
        return {}
    out = {f: 0.0 for f in features}
    for col, v in zip(columns, imp):
        for f in features:
            if col.startswith(f + "_"):
                out[f] += float(v)
                break
    total = sum(out.values()) or 1.0
    return {k: round(v / total, 4) for k, v in sorted(out.items(), key=lambda kv: -kv[1])}


def _fit(model, X, y):
    """Fit with square-root balanced sample weights: rare classes (Fatal) count more, without the
    accuracy collapse that fully balanced weights cause on this data."""
    weights = compute_sample_weight("balanced", y) ** 0.5
    model.fit(X, y, sample_weight=weights)
    return model


def _cv_accuracy(model, X, y, cv):
    scores = []
    for tr, te in cv.split(X, y):
        m = _fit(clone(model), X.iloc[tr], y[tr])
        scores.append(accuracy_score(y[te], m.predict(X.iloc[te])))
    return np.array(scores)


def train_models(user=None):
    """Train Random Forest and XGBoost on approved data, store metrics, persist the best model."""
    qs = approved_accidents().values(*FEATURES, "severity")
    df = pd.DataFrame.from_records(qs)
    if len(df) < 100:
        raise TrainingError("At least 100 approved accident records are needed to train. Upload and approve a dataset first.")
    if df["severity"].nunique() < 2:
        raise TrainingError("The data must contain at least two different severity classes.")
    features = usable_features(df)
    if not features:
        raise TrainingError("No usable feature columns found in the data.")

    X = pd.get_dummies(df[features].astype(str))
    encoder = LabelEncoder().fit(df["severity"])
    y = encoder.transform(df["severity"])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    candidates = {"Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=42, n_jobs=-1)}
    if XGBClassifier is not None:
        candidates["XGBoost"] = XGBClassifier(n_estimators=250, max_depth=4, learning_rate=0.05, subsample=0.9,
                                              colsample_bytree=0.9, eval_metric="mlogloss", random_state=42, n_jobs=-1)

    classes = list(encoder.classes_)
    order = [classes.index(s) for s in SEVERITIES if s in classes]
    labels = [classes[i] for i in order]
    baseline = float(np.bincount(y_test).max() / len(y_test))          # always predict the majority class
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    results = {}
    for name, model in candidates.items():
        _fit(model, X_train, y_train)
        pred = model.predict(X_test)
        cvs = _cv_accuracy(model, X, y, cv)
        rep = classification_report(y_test, pred, labels=order, target_names=labels, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_test, pred, labels=order)
        results[name] = {
            "model": model,
            "accuracy": accuracy_score(y_test, pred),
            "precision": precision_score(y_test, pred, average="weighted", zero_division=0),
            "recall": recall_score(y_test, pred, average="weighted", zero_division=0),
            "f1": f1_score(y_test, pred, average="weighted", zero_division=0),
            "f1_macro": f1_score(y_test, pred, average="macro", zero_division=0),
            "cv_mean": float(cvs.mean()), "cv_std": float(cvs.std()),
            "details": {
                "labels": labels,
                "confusion": cm.tolist(),
                "per_class": {k: {"precision": round(float(rep[k]["precision"]), 3), "recall": round(float(rep[k]["recall"]), 3),
                                  "f1": round(float(rep[k]["f1-score"]), 3), "support": int(rep[k]["support"])} for k in labels},
                "importance": _aggregate_importance(model, list(X.columns), features),
                "test_size": int(len(y_test)), "train_size": int(len(y_train)),
            },
        }

    best = max(results, key=lambda k: results[k]["f1"])
    choices = {f: sorted(v for v in df[f].unique() if v != "Unknown") for f in features}
    joblib.dump({"model": results[best]["model"], "columns": list(X.columns), "encoder": encoder,
                 "name": best, "features": features, "choices": choices}, _model_path())
    _cache["bundle"] = None

    run_id = uuid.uuid4().hex[:12]
    MLModel.objects.update(is_best=False)
    saved = []
    for name, r in results.items():
        saved.append(MLModel.objects.create(
            run_id=run_id, algorithm=name, accuracy=r["accuracy"], precision=r["precision"], recall=r["recall"],
            f1_score=r["f1"], f1_macro=r["f1_macro"], cv_mean=r["cv_mean"], cv_std=r["cv_std"],
            baseline_accuracy=baseline, n_samples=len(df), details=r["details"],
            is_best=(name == best), trained_by=user))
    return best, saved


def load_bundle():
    path = _model_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _cache["bundle"] is None or _cache["mtime"] != mtime:
        _cache["bundle"] = joblib.load(path)
        _cache["mtime"] = mtime
    return _cache["bundle"]


def model_ready():
    return _model_path().exists()


def predict(conditions):
    """conditions: dict with the model's feature keys. Returns (label, {class: probability}, model_name)."""
    bundle = load_bundle()
    if bundle is None:
        raise TrainingError("No trained model found. Ask an administrator to train the models first.")
    row = pd.DataFrame([{f: str(conditions.get(f, "Unknown")) for f in bundle["features"]}])
    X = pd.get_dummies(row).reindex(columns=bundle["columns"], fill_value=0)
    proba = bundle["model"].predict_proba(X)[0]
    probs = {cls: float(p) for cls, p in zip(bundle["encoder"].classes_, proba)}
    label = max(probs, key=probs.get)
    ordered = {s: round(probs.get(s, 0.0), 4) for s in SEVERITIES if s in probs}
    return label, ordered, bundle["name"]
