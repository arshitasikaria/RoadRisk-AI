from django import forms
from django.contrib.auth.forms import UserCreationForm

from . import ml
from .constants import FEATURE_LABELS
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.ROLE_PUBLIC
        if commit:
            user.save()
        return user


class PredictForm(forms.Form):
    """Fields are built from the features the trained model actually uses."""
    road_name = forms.CharField(max_length=150, required=False, label="Road stretch (optional)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bundle = ml.load_bundle() or {"features": [], "choices": {}}
        self.model_features = bundle["features"]
        for f in self.model_features:
            opts = bundle["choices"].get(f, [])
            self.fields[f] = forms.ChoiceField(choices=[(v, v) for v in opts], label=FEATURE_LABELS.get(f, f))
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-select" if isinstance(field, forms.ChoiceField) else "form-control"
        self.fields["road_name"].widget.attrs.update({"list": "roadlist", "placeholder": "e.g. Pune-Solapur NH-9 km 180-190"})


class DatasetUploadForm(forms.Form):
    name = forms.CharField(max_length=150, label="Dataset name")
    file = forms.FileField(label="CSV file")
    approve = forms.BooleanField(required=False, initial=True, label="Approve immediately (include in analytics and training)")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a .csv file.")
        if f.size > 50 * 1024 * 1024:
            raise forms.ValidationError("File is larger than 50 MB.")
        return f
