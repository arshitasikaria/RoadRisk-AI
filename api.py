"""REST API (Django REST Framework). Authenticate with a logged-in session or HTTP Basic auth."""
from rest_framework.response import Response
from rest_framework.views import APIView

from . import analytics, ml
from .models import Prediction, Recommendation
from .recommendations import build_recommendations


class PredictAPI(APIView):
    """POST the model's input fields (see GET /api/predict/ for the list and allowed values)."""

    def get(self, request):
        bundle = ml.load_bundle()
        if bundle is None:
            return Response({"error": "No trained model."}, status=503)
        return Response({"features": bundle["features"], "choices": bundle["choices"]})

    def post(self, request):
        bundle = ml.load_bundle()
        if bundle is None:
            return Response({"error": "No trained model. Train the models first."}, status=503)
        missing = [f for f in bundle["features"] if not request.data.get(f)]
        if missing:
            return Response({"error": "Missing fields: " + ", ".join(missing)}, status=400)
        cond = {f: str(request.data[f]) for f in bundle["features"]}
        label, probs, model_name = ml.predict(cond)
        recs = build_recommendations(label, cond)
        pred = Prediction.objects.create(user=request.user, road_name=request.data.get("road_name", ""), conditions=cond,
                                         predicted_severity=label, confidence=probs[label], probabilities=probs, model_used=model_name)
        Recommendation.objects.bulk_create([Recommendation(prediction=pred, suggestion_text=t) for t in recs])
        return Response({"prediction_id": pred.pk, "severity": label, "confidence": probs[label],
                         "probabilities": probs, "model": model_name, "recommendations": recs})


class StatsAPI(APIView):
    def get(self, request):
        year = request.query_params.get("year")
        return Response(analytics.dashboard_data(int(year) if year else None, request.query_params.get("corridor") or None))


class RoadRiskAPI(APIView):
    def get(self, request):
        q = request.query_params.get("q", "")
        return Response(analytics.search_roads(q) if q else [])
