"""Run with:  python manage.py test"""
import io
import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from core.models import Accident, Dataset, MLModel, Prediction, RegionStat, User

TMP = Path(tempfile.mkdtemp())


@override_settings(MODEL_DIR=TMP / "models", MEDIA_ROOT=TMP / "media")
class RoadRiskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_project", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def login(self, name):
        self.client.login(username=name, password=f"{name}123")

    def prediction_payload(self):
        from core import ml
        b = ml.load_bundle()
        data = {f: b["choices"][f][0] for f in b["features"]}
        data["road_name"] = "Pune-Solapur NH-9 km 180-190"
        return data

    def test_data_loaded(self):
        self.assertGreater(Accident.objects.count(), 3500)
        self.assertEqual(RegionStat.objects.filter(category="state").count(), 28)
        self.assertEqual(Accident.objects.filter(corridor="Pune-Solapur (NH-9)").exists(), True)
        self.assertEqual(MLModel.objects.filter(is_best=True).count(), 1)

    def test_public_pages(self):
        for url in ["/", "/login/", "/register/", "/search/", "/search/?q=pune", "/india-statistics/",
                    "/india-statistics/?type=city&sort=rate"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_guest_redirected(self):
        for url in ["/predict/", "/dashboard/", "/predictions/", "/manage/datasets/"]:
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_register_creates_public_user(self):
        r = self.client.post("/register/", {"username": "newbie", "email": "n@x.com", "password1": "Str0ngPass!9", "password2": "Str0ngPass!9"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(User.objects.get(username="newbie").role, "public")

    def test_login_wrong_password(self):
        r = self.client.post("/login/", {"username": "admin", "password": "wrong"})
        self.assertContains(r, "Invalid username or password")

    def test_role_based_access(self):
        self.login("public")
        self.assertEqual(self.client.get("/manage/datasets/").status_code, 403)
        self.assertEqual(self.client.get("/reports/analytics.xlsx").status_code, 403)
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)
        self.client.logout(); self.login("analyst")
        self.assertEqual(self.client.get("/reports/analytics.xlsx").status_code, 200)
        self.assertEqual(self.client.get("/manage/models/").status_code, 403)
        self.client.logout(); self.login("admin")
        for url in ["/manage/datasets/", "/manage/models/", "/manage/users/", "/manage/powerbi/", "/manage/powerbi/export.csv"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_prediction_flow_and_reports(self):
        self.login("public")
        self.assertEqual(self.client.get("/predict/").status_code, 200)
        r = self.client.post("/predict/", self.prediction_payload())
        self.assertEqual(r.status_code, 302)
        p = Prediction.objects.get()
        self.assertIn(p.predicted_severity, ["Fatal", "Serious", "Minor"])
        self.assertTrue(p.recommendations.exists())
        self.assertEqual(self.client.get(r.url).status_code, 200)
        pdf = self.client.get(f"/predictions/{p.pk}/report.pdf")
        self.assertTrue(b"".join(pdf.streaming_content).startswith(b"%PDF"))
        self.assertEqual(self.client.get(f"/predictions/{p.pk}/report.xlsx").status_code, 200)
        self.assertEqual(self.client.get("/predictions/").status_code, 200)

    def test_empty_prediction_rejected(self):
        self.login("public")
        r = self.client.post("/predict/", {"road_name": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_other_users_cannot_see_prediction(self):
        self.login("public"); self.client.post("/predict/", self.prediction_payload())
        p = Prediction.objects.get()
        User.objects.create_user("other", password="other123")
        self.client.logout(); self.client.login(username="other", password="other123")
        self.assertEqual(self.client.get(f"/predictions/{p.pk}/").status_code, 404)

    def test_dashboard_data_and_filters(self):
        self.login("public")
        d = self.client.get("/dashboard/data/").json()          # default corridor = Pune-Solapur
        self.assertEqual(len(d["monthly"]), 12)
        self.assertTrue(d["roads"])
        allc = self.client.get("/dashboard/data/?corridor=all").json()
        self.assertGreater(allc["kpis"]["total"], d["kpis"]["total"])
        self.assertEqual(self.client.get("/dashboard/?corridor=all&year=2016").status_code, 200)

    def test_road_profile(self):
        r = self.client.get("/search/?q=Pune")
        self.assertContains(r, "Pune-Solapur")
        road = Accident.objects.filter(corridor="Pune-Solapur (NH-9)").values_list("road_name", flat=True).first()
        self.assertContains(self.client.get("/search/", {"road": road}), "Risk index")

    def test_upload_valid_invalid_and_duplicates(self):
        self.login("admin")
        bad = io.BytesIO(b"a,b\n1,2\n"); bad.name = "bad.csv"
        self.assertContains(self.client.post("/manage/datasets/", {"name": "bad", "file": bad, "approve": "on"}), "Missing required column")
        good = io.BytesIO(("road_name,weather,time_of_day,vehicle_type,severity,date\n"
                           "Test Rd,Rain,Night,Truck,Fatal,2024-03-05\nTest Rd,Rain,Night,Truck,Fatal,2024-03-05\n"
                           "Test Rd,Clear,Morning,Car,slight,2024-04-01\n").encode())
        good.name = "good.csv"
        self.assertEqual(self.client.post("/manage/datasets/", {"name": "good", "file": good, "approve": "on"}).status_code, 302)
        ds = Dataset.objects.get(name="good")
        self.assertEqual((ds.rows_count, ds.duplicates_removed), (2, 1))

    def test_train_and_api(self):
        self.login("admin")
        self.assertEqual(self.client.post("/manage/models/").status_code, 302)
        best = MLModel.objects.get(is_best=True)
        self.assertIn("confusion", best.details)
        self.assertEqual(self.client.get("/manage/models/").status_code, 200)
        r = self.client.post("/api/predict/", self.prediction_payload())
        self.assertEqual(r.status_code, 200)
        self.assertIn("severity", r.json())
        self.assertEqual(self.client.post("/api/predict/", {"weather": "Fine"}).status_code, 400)
        self.assertEqual(self.client.get("/api/stats/").status_code, 200)
