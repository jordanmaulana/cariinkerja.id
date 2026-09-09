"""Stop probing Indeed/JobStreet/LinkedIn.

They were dropped from the generated crawl URL set on 2026-09-09, so a daily ❌
in the Discord health report is noise rather than signal. Re-enable from
``/crawl-health/`` if one of them comes back.
"""

from django.db import migrations

LEGACY_SOURCES = ("indeed", "jobstreet", "linkedin")


def deactivate(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(source__in=LEGACY_SOURCES).update(is_active=False)


def reactivate(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(source__in=LEGACY_SOURCES).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0016_seed_new_source_crawl_health"),
    ]

    operations = [
        migrations.RunPython(deactivate, reactivate),
    ]
