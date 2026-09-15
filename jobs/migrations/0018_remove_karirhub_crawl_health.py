"""Stop probing Karirhub, and drop it from the source choices.

Karirhub was removed outright on 2026-09-09 for low volume and low quality, so
unlike the Indeed/JobStreet/LinkedIn retirement in 0017 there is no scraper left
to re-enable. The seeded row is deleted rather than deactivated: with "karirhub"
gone from ``SOURCE_CHOICES`` an inactive row would hold a value the
``/crawl-health/`` admin form can no longer validate, so any later edit of it
would fail.
"""

from django.db import migrations, models

LABEL = "Karirhub default"


def unseed_karirhub(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(label=LABEL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0017_deactivate_legacy_crawl_health"),
    ]

    operations = [
        migrations.RunPython(unseed_karirhub, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="crawlhealthtarget",
            name="source",
            field=models.CharField(
                choices=[
                    ("indeed", "Indeed"),
                    ("jobstreet", "Jobstreet"),
                    ("linkedin", "LinkedIn"),
                    ("dealls", "Dealls"),
                    ("kalibrr", "Kalibrr"),
                    ("kitalulus", "Kitalulus"),
                ],
                max_length=20,
            ),
        ),
    ]
