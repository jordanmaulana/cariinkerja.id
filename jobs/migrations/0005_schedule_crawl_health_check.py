from django.db import migrations

PERIODIC_TASK_NAME = "crawl-health-check-daily"
TASK_PATH = "jobs.tasks.crawl_health_check"


def create_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="6",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="Asia/Jakarta",
    )
    PeriodicTask.objects.update_or_create(
        name=PERIODIC_TASK_NAME,
        defaults={
            "crontab": schedule,
            "task": TASK_PATH,
            "enabled": True,
            "description": "Daily 06:00 Asia/Jakarta — probe Indeed + Jobstreet scrapers, report to Discord.",
        },
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0004_job_company"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
