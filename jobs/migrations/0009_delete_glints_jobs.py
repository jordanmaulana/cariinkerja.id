from django.db import migrations


def delete_glints_jobs(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(source="glints").delete()  # cascades to Assessment rows


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0008_alter_crawlhealthtarget_source"),
        ("assessment", "0007_schedule_morning_email"),
    ]

    operations = [
        migrations.RunPython(delete_glints_jobs, migrations.RunPython.noop),
    ]
