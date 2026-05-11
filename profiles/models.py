from django.conf import settings
from django.db import models

from profiles.consts import Status
from core.models import BaseModel


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
    phone = models.CharField(max_length=32, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    full_profile = models.TextField(
        null=True, blank=True, help_text="LLM-cleaned LinkedIn content"
    )
    linkedin_raw = models.TextField(
        null=True, blank=True, help_text="Raw LinkedIn paste (audit / re-run source)"
    )
    linkedin_ingested_at = models.DateTimeField(null=True, blank=True)
    open_to_work = models.BooleanField(default=False)
    linkedin_quality_ok = models.BooleanField(default=False)
    linkedin_quality_reason = models.TextField(blank=True, default="")
    whitelist = models.BooleanField(
        default=False,
        help_text="Bypass plan limits (preference cap, future crawl caps).",
    )

    class Meta:
        app_label = "profiles"
        indexes = [
            models.Index(fields=["linkedin_quality_ok"]),
        ]

    @property
    def linkedin_discount_eligible(self) -> bool:
        return bool(self.open_to_work)


class Preference(BaseModel):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="preferences"
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    job_type = models.JSONField(default=list, blank=True)
    remote_option = models.JSONField(default=list, blank=True)
    crawl_urls = models.JSONField(default=list, blank=True, help_text="Filled by Admin")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING_ADMIN
    )

    class Meta:
        app_label = "profiles"
        indexes = [
            models.Index(fields=["status"]),
        ]
