from django.db import models

from profiles.consts import Status
from core.models import BaseModel
from jobs.consts import JobType, RemoteOption


class Profile(BaseModel):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    full_profile = models.TextField(null=True, blank=True)

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
    crawl_url = models.URLField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING
    )

    class Meta:
        app_label = "profiles"
