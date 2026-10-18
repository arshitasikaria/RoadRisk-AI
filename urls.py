from django.contrib.auth import views as auth_views
from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("search/", views.road_search, name="search"),
    path("india-statistics/", views.states, name="states"),

    path("predict/", views.predict_view, name="predict"),
    path("predictions/", views.history, name="history"),
    path("predictions/<int:pk>/", views.prediction_detail, name="prediction_detail"),
    path("predictions/<int:pk>/report.pdf", views.report_pdf, name="report_pdf"),
    path("predictions/<int:pk>/report.xlsx", views.report_excel, name="report_excel"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("reports/analytics.xlsx", views.analytics_report, name="analytics_report"),

    path("manage/datasets/", views.dataset_list, name="dataset_list"),
    path("manage/datasets/<int:pk>/<str:action>/", views.dataset_action, name="dataset_action"),
    path("manage/models/", views.train_view, name="train"),
    path("manage/users/", views.user_list, name="user_list"),
    path("manage/powerbi/", views.powerbi, name="powerbi"),
    path("manage/powerbi/export.csv", views.powerbi_export, name="powerbi_export"),

    path("api/predict/", api.PredictAPI.as_view(), name="api_predict"),
    path("api/stats/", api.StatsAPI.as_view(), name="api_stats"),
    path("api/road-risk/", api.RoadRiskAPI.as_view(), name="api_road_risk"),
]
