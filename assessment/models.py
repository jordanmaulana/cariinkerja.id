from django.db import models

from assessment.consts import Status
from core.models import BaseModel


# Create your models here.
class Assessment(BaseModel):
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, related_name="assessments"
    )
    preference = models.ForeignKey(
        "profiles.Preference", on_delete=models.CASCADE, related_name="assessments"
    )
    soft_skill_match = models.JSONField(default=list, blank=True)
    soft_skill_gap = models.JSONField(default=list, blank=True)
    hard_skill_match = models.JSONField(default=list, blank=True)
    hard_skill_gap = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )

    score = models.IntegerField()

    class Meta:
        app_label = "assessment"
