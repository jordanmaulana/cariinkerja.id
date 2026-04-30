from django.db import models


class JobType(models.TextChoices):
    FULL_TIME = "full-time", "Full-time"
    PART_TIME = "part-time", "Part-time"
    CONTRACT = "contract", "Contract"
    INTERNSHIP = "internship", "Internship"


class RemoteOption(models.TextChoices):
    REMOTE = "remote", "Remote"
    ON_SITE = "on-site", "On-site"
    HYBRID = "hybrid", "Hybrid"
