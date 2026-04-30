from django.db import models

from core.models import make_object_id
from jobs.consts import JobType, RemoteOption


# Create your models here.
class Job(models.Model):
    id = models.CharField(primary_key=True, default=make_object_id, editable=False)
    url = models.URLField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255, null=True, blank=True)
    job_type = models.CharField(
        max_length=20, choices=JobType.choices, null=True, blank=True
    )
    remote_option = models.CharField(
        max_length=20, choices=RemoteOption.choices, null=True, blank=True
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_on"]
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        return f"{self.id}"
