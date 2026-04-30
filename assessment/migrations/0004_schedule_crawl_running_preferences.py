from django.db import migrations

PERIODIC_TASK_NAME = "crawl-running-preferences-daily"
TASK_PATH = "assessment.tasks.crawl_running_preferences"


def create_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="5",
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
            "description": "Daily 05:00 Asia/Jakarta — fan out crawl + assessment for running Preferences.",
        },
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("assessment", "0003_assessment_verdict"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
