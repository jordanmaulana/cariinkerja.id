from django import forms

from core.models import Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "price", "preference_limit", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full px-3 py-2 border rounded"}),
            "price": forms.NumberInput(
                attrs={"class": "w-full px-3 py-2 border rounded", "min": 0}
            ),
            "preference_limit": forms.NumberInput(
                attrs={"class": "w-full px-3 py-2 border rounded", "min": 1}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "size-4"}),
        }
