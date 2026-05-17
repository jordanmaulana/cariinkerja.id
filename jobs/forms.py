from django import forms

from jobs.models import CrawlHealthTarget

INPUT_CLS = "w-full px-3 py-2 border rounded"


class CrawlHealthTargetForm(forms.ModelForm):
    class Meta:
        model = CrawlHealthTarget
        fields = ["label", "source", "url", "is_active"]
        widgets = {
            "label": forms.TextInput(attrs={"class": INPUT_CLS}),
            "source": forms.Select(attrs={"class": INPUT_CLS}),
            "url": forms.URLInput(attrs={"class": INPUT_CLS}),
            "is_active": forms.CheckboxInput(attrs={"class": "size-4"}),
        }
