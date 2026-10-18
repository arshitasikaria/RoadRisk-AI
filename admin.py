from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Accident, Dataset, MLModel, Prediction, Recommendation, RegionStat, Report, User


@admin.register(User)
class RoadRiskUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("RoadRisk role", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff")


for m in (Dataset, Accident, MLModel, Prediction, Recommendation, Report, RegionStat):
    admin.site.register(m)
