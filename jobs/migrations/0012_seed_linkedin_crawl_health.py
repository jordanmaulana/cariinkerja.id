from django.db import migrations

LABEL = "LinkedIn default"


def seed_linkedin(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.get_or_create(
        label=LABEL,
        defaults={
            "label": LABEL,
            "source": "linkedin",
            "url": "https://www.linkedin.com/jobs/search/?keywords=mobile%20developer&geoId=102478259",
            "is_active": True,
        },
    )


def unseed_linkedin(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(label=LABEL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0011_job_hard_skills_job_soft_skills"),
    ]

    operations = [
        migrations.RunPython(seed_linkedin, unseed_linkedin),
    ]
