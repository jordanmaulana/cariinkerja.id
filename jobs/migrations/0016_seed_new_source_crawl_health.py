from django.db import migrations

TARGETS = [
    (
        "Kalibrr default",
        "kalibrr",
        "https://www.kalibrr.com/job-board/te/software-engineer/co/Indonesia",
    ),
    (
        "Kitalulus default",
        "kitalulus",
        "https://www.kitalulus.com/lowongan/in-jakarta-selatan",
    ),
    (
        "Karirhub default",
        "karirhub",
        "https://karirhub.kemnaker.go.id/lowongan-dalam-negeri",
    ),
]


def seed_targets(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    for label, source, url in TARGETS:
        CrawlHealthTarget.objects.get_or_create(
            label=label,
            defaults={
                "label": label,
                "source": source,
                "url": url,
                "is_active": True,
            },
        )


def unseed_targets(apps, schema_editor):
    CrawlHealthTarget = apps.get_model("jobs", "CrawlHealthTarget")
    CrawlHealthTarget.objects.filter(
        label__in=[label for label, _, _ in TARGETS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0015_alter_crawlhealthtarget_source"),
    ]

    operations = [
        migrations.RunPython(seed_targets, unseed_targets),
    ]
