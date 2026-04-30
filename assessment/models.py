from django.db import models

from core.models import BaseModel


# Create your models here.
class Assessment(BaseModel):
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, related_name="assessments"
    )
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="assessments"
    )
    soft_skill_match = models.JSONField(default=list, blank=True)
    soft_skill_gap = models.JSONField(default=list, blank=True)
    hard_skill_match = models.JSONField(default=list, blank=True)
    hard_skill_gap = models.JSONField(default=list, blank=True)

    score = models.IntegerField()

    class Meta:
        app_label = "assessment"
