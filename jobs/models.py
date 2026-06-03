from django.db import models

from core.models import BaseModel, make_object_id
from jobs.consts import JobType, RemoteOption


class CrawlHealthTarget(BaseModel):
    SOURCE_INDEED = "indeed"
    SOURCE_JOBSTREET = "jobstreet"
    SOURCE_LINKEDIN = "linkedin"
    SOURCE_CHOICES = [
        (SOURCE_INDEED, "Indeed"),
        (SOURCE_JOBSTREET, "Jobstreet"),
        (SOURCE_LINKEDIN, "LinkedIn"),
    ]

    label = models.CharField(max_length=120)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "jobs"
        ordering = ["label"]

    def __str__(self):
        return f"{self.label} ({self.source})"


class Job(models.Model):
    id = models.CharField(primary_key=True, default=make_object_id, editable=False)
    url = models.URLField(unique=True)
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    location = models.CharField(max_length=255, null=True, blank=True)
    job_type = models.CharField(
        max_length=20, choices=JobType.choices, null=True, blank=True
    )
    remote_option = models.CharField(
        max_length=20, choices=RemoteOption.choices, null=True, blank=True
    )
    source = models.CharField(max_length=255, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_on"]
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        return f"{self.id}"
