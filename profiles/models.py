from django.conf import settings
from django.db import models

from profiles.consts import Source, Status
from core.models import BaseModel
from jobs.consts import JobType, RemoteOption


class Profile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acted_profiles",
    )
    full_name = models.CharField(max_length=255, null=True, blank=True)
    suggested_full_name = models.CharField(max_length=255, blank=True, default="")
    linkedin_url = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    full_profile = models.TextField(null=True, blank=True, help_text="Filled by Admin")

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
    crawl_url = models.URLField(null=True, blank=True, help_text="Filled by Admin")
    crawl_source = models.CharField(
        max_length=20,
        choices=Source.choices,
        null=True,
        blank=True,
        help_text="Filled by Admin",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING_PAYMENT
    )

    class Meta:
        app_label = "profiles"
