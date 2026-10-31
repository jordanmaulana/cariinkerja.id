from django.db import migrations, models

LABEL = "Workable default"


def seed_workable(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.get_or_create(
        label=LABEL,
        defaults={
            "source": "workable",
            "url": "https://jobs.workable.com/search?query=sales&location=Indonesia",
            "is_active": True,
        },
    )


def unseed_workable(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(label=LABEL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0016_jobicy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crawlhealthtarget",
            name="source",
            field=models.CharField(
                choices=[
                    ("indeed", "Indeed"),
                    ("jobstreet", "Jobstreet"),
                    ("linkedin", "LinkedIn"),
                    ("dealls", "Dealls"),
                    ("himalayas", "Himalayas"),
                    ("jobicy", "Jobicy"),
                    ("workable", "Workable"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(seed_workable, unseed_workable),
    ]
