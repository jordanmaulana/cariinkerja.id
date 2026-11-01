from django.db import migrations

PERIODIC_TASK_NAME = "refresh-skill-maps-weekly"
TASK_PATH = "jobs.tasks.refresh_skill_maps"


def create_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # An admin may have scheduled it by hand already; don't add a second copy.
    if (
        PeriodicTask.objects.filter(task=TASK_PATH)
        .exclude(name=PERIODIC_TASK_NAME)
        .exists()
    ):
        return
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="7",
        day_of_week="1",
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
            "description": "Monday 07:00 Asia/Jakarta — write this week's Skill Map snapshots.",
        },
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0019_skill_map"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
