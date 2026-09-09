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


# Identifying User-Agent for scrapers that do not need to impersonate a browser.
# Kalibrr, Kitalulus and Karirhub all serve full content to this UA (verified
# 2026-09-09), so those scrapers announce themselves rather than spoofing a TLS
# fingerprint the way the Indeed/LinkedIn scrapers do. See _docs/scraping-policy.md.
BOT_USER_AGENT = "CariinKerjaBot/1.0 (+https://cariinkerja.id)"
