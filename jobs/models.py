from django.db import models

from core.models import BaseModel, make_object_id
from jobs.consts import JobType, RemoteOption


class CrawlHealthTarget(BaseModel):
    SOURCE_INDEED = "indeed"
    SOURCE_JOBSTREET = "jobstreet"
    SOURCE_LINKEDIN = "linkedin"
    SOURCE_DEALLS = "dealls"
    SOURCE_HIMALAYAS = "himalayas"
    SOURCE_JOBICY = "jobicy"
    SOURCE_WORKABLE = "workable"
    SOURCE_REMOTEOK = "remoteok"
    SOURCE_CHOICES = [
        (SOURCE_INDEED, "Indeed"),
        (SOURCE_JOBSTREET, "Jobstreet"),
        (SOURCE_LINKEDIN, "LinkedIn"),
        (SOURCE_DEALLS, "Dealls"),
        (SOURCE_HIMALAYAS, "Himalayas"),
        (SOURCE_JOBICY, "Jobicy"),
        (SOURCE_WORKABLE, "Workable"),
        (SOURCE_REMOTEOK, "Remote OK"),
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
    hard_skills = models.JSONField(default=list, blank=True)
    soft_skills = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)
    # Set by sources that publish an expiry (Himalayas) or that we see vanish
    # from a full feed (Workable); SPA labels it.
    expires_at = models.DateTimeField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_on"]
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        return f"{self.id}"


class SkillMapPage(BaseModel):
    """A public /skill/<slug>/ page: the most-requested skills for one title."""

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(
        max_length=120, help_text='Shown on the page, e.g. "Data Analyst".'
    )
    match_words = models.CharField(
        max_length=200,
        blank=True,
        help_text="Every word must appear in the job title. Empty = use the title.",
    )
    exclude_words = models.CharField(
        max_length=200,
        blank=True,
        help_text="A job title containing any of these words is left out.",
    )
    is_published = models.BooleanField(default=False)
    min_jobs = models.PositiveIntegerField(
        default=30, help_text="Below this many jobs the page stays hidden."
    )

    class Meta:
        app_label = "jobs"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def latest_snapshot(self):
        return self.snapshots.order_by("-computed_on", "-created_on").first()


class SkillMapSnapshot(BaseModel):
    """One weekly count for a SkillMapPage. Old rows are kept for trends."""

    page = models.ForeignKey(
        SkillMapPage, on_delete=models.CASCADE, related_name="snapshots"
    )
    computed_on = models.DateField()
    window_days = models.PositiveIntegerField()
    job_count = models.PositiveIntegerField()
    data = models.JSONField(default=dict)

    class Meta:
        app_label = "jobs"
        ordering = ["-computed_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["page", "computed_on"], name="uniq_skillmap_snapshot_per_day"
            )
        ]

    def __str__(self):
        return f"{self.page} @ {self.computed_on}"
