from django import forms

from billing.models import Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "price", "preference_limit", "duration_days", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full px-3 py-2 border rounded"}),
            "price": forms.NumberInput(
                attrs={"class": "w-full px-3 py-2 border rounded", "min": 0}
            ),
            "preference_limit": forms.NumberInput(
                attrs={"class": "w-full px-3 py-2 border rounded", "min": 1}
            ),
            "duration_days": forms.NumberInput(
                attrs={"class": "w-full px-3 py-2 border rounded", "min": 1}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "size-4"}),
        }
