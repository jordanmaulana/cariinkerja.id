from django.db import migrations

LABEL = "Dealls default"


def seed_dealls(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.get_or_create(
        label=LABEL,
        defaults={
            "label": LABEL,
            "source": "dealls",
            "url": "https://dealls.com/?location=remote&employment=partTime&employment=freelance",
            "is_active": True,
        },
    )


def unseed_dealls(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(label=LABEL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0013_alter_crawlhealthtarget_source"),
    ]

    operations = [
        migrations.RunPython(seed_dealls, unseed_dealls),
    ]
