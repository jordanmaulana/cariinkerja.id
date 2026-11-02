"""Stop probing Remote OK, and drop it from the source choices.

Remote OK was removed on 2026-11-02: its job pages make the applicant pay
before applying. The rows are deleted rather than deactivated, as in 0021:
with the value gone from ``SOURCE_CHOICES`` an inactive row could no longer be
saved through the ``/crawl-health/`` admin form.
"""

from django.db import migrations, models


def delete_targets(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(source="remoteok").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0022_alter_job_url"),
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
                ],
                max_length=20,
            ),
        ),
    ]
