"""Stop probing Indeed and JobStreet, and drop them from the source choices.

Both scrapers were removed on 2026-11-01: they had failed the daily health
check behind Cloudflare since 2026-09-09. The rows are deleted rather than
deactivated: with the values gone from ``SOURCE_CHOICES`` an inactive row could
no longer be saved through the ``/crawl-health/`` admin form.
"""

from django.db import migrations, models


def delete_targets(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(source__in=["indeed", "jobstreet"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0020_schedule_skill_map_refresh"),
    ]

    operations = [
        migrations.RunPython(delete_targets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="crawlhealthtarget",
            name="source",
            field=models.CharField(
                choices=[
                    ("linkedin", "LinkedIn"),
                    ("dealls", "Dealls"),
                    ("himalayas", "Himalayas"),
                    ("jobicy", "Jobicy"),
                    ("workable", "Workable"),
                    ("remoteok", "Remote OK"),
                ],
                max_length=20,
            ),
        ),
    ]
