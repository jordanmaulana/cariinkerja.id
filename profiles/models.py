from django.db import models

from core.models import BaseModel
from jobs.consts import JobType, RemoteOption


class Profile(BaseModel):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    class Meta:
        app_label = "profiles"


class Preference(BaseModel):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="preferences"
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    job_type = models.CharField(
        max_length=20, choices=JobType.choices, null=True, blank=True
    )
    remote_option = models.CharField(
        max_length=20, choices=RemoteOption.choices, null=True, blank=True
    )

    class Meta:
        app_label = "profiles"
