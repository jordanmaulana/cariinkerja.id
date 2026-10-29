from django.db import migrations, models

LABEL = "Remote OK default"


def seed_remoteok(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.get_or_create(
        label=LABEL,
        defaults={
            "source": "remoteok",
            "url": "https://remoteok.com/api?search=engineer",
            "is_active": True,
        },
    )


def unseed_remoteok(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(label=LABEL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0017_workable"),
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
                    ("remoteok", "Remote OK"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(seed_remoteok, unseed_remoteok),
    ]
