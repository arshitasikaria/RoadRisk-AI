from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN, ROLE_ANALYST, ROLE_PUBLIC = "admin", "analyst", "public"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Administrator"),
        (ROLE_ANALYST, "Traffic Analyst"),
        (ROLE_PUBLIC, "Public User"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PUBLIC)

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.ROLE_ADMIN

    @property
    def is_analyst_role(self):
        return self.is_admin_role or self.role == self.ROLE_ANALYST

    @property
    def role_label(self):
        return "Administrator" if self.is_superuser else self.get_role_display()


class Dataset(models.Model):
    STATUS_CHOICES = [("pending", "Pending approval"), ("approved", "Approved")]
    name = models.CharField(max_length=150)
    file = models.FileField(upload_to="datasets/", blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="approved")
    rows_count = models.PositiveIntegerField(default=0)
    duplicates_removed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name


class Accident(models.Model):
    dataset = models.ForeignKey(Dataset, null=True, blank=True, on_delete=models.CASCADE, related_name="accidents")
    date = models.DateField(null=True, blank=True)
    road_name = models.CharField(max_length=150, db_index=True)
    corridor = models.CharField(max_length=80, default="Unknown", db_index=True)
    area_type = models.CharField(max_length=30, default="Unknown")
    road_type = models.CharField(max_length=40, default="Unknown")
    road_condition = models.CharField(max_length=40, default="Unknown")
    weather = models.CharField(max_length=30)
    time_of_day = models.CharField(max_length=20)
    day_of_week = models.CharField(max_length=12, default="Unknown")
    vehicle_type = models.CharField(max_length=40)
    cause = models.CharField(max_length=60, default="Unknown")
    severity = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.road_name} - {self.severity}"


class MLModel(models.Model):
    run_id = models.CharField(max_length=20, db_index=True, default="")
    algorithm = models.CharField(max_length=40)
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    f1_macro = models.FloatField(default=0)
    cv_mean = models.FloatField(default=0)
    cv_std = models.FloatField(default=0)
    baseline_accuracy = models.FloatField(default=0)
    n_samples = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)   # confusion matrix, per-class metrics, feature importance
    is_best = models.BooleanField(default=False)
    trained_at = models.DateTimeField(auto_now_add=True)
    trained_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-trained_at", "-f1_score"]

    def __str__(self):
        return f"{self.algorithm} ({self.f1_score:.3f})"


class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions")
    accident = models.ForeignKey(Accident, null=True, blank=True, on_delete=models.SET_NULL)
    road_name = models.CharField(max_length=150, blank=True)
    conditions = models.JSONField(default=dict)
    predicted_severity = models.CharField(max_length=10)
    confidence = models.FloatField(default=0)
    probabilities = models.JSONField(default=dict, blank=True)
    model_used = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def condition_summary(self):
        return " \u00b7 ".join(list(self.conditions.values())[:4])

    def __str__(self):
        return f"Prediction #{self.pk}: {self.predicted_severity}"


class Report(models.Model):
    prediction = models.OneToOneField(Prediction, on_delete=models.CASCADE, related_name="report")
    generated_on = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="reports/")

    def __str__(self):
        return f"Report for prediction #{self.prediction_id}"


class Recommendation(models.Model):
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name="recommendations")
    suggestion_text = models.TextField()

    def __str__(self):
        return f"Recommendation for prediction #{self.prediction_id}"


class RegionStat(models.Model):
    """Real state / UT / city level road accident statistics (NCRB ADSI Table 1A.2)."""
    STATE, UT, CITY = "state", "ut", "city"
    CATEGORY_CHOICES = [(STATE, "State"), (UT, "Union Territory"), (CITY, "City")]
    category = models.CharField(max_length=6, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=120)
    road_cases = models.PositiveIntegerField(default=0)
    road_injured = models.PositiveIntegerField(default=0)
    road_died = models.PositiveIntegerField(default=0)
    total_cases = models.PositiveIntegerField(default=0)
    total_died = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category", "name"]

    @property
    def deaths_per_100(self):
        return round(self.road_died / self.road_cases * 100, 1) if self.road_cases else 0.0

    @property
    def injured_per_100(self):
        return round(self.road_injured / self.road_cases * 100, 1) if self.road_cases else 0.0

    def __str__(self):
        return f"{self.name} ({self.category})"
