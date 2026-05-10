import json

from django.db import migrations, models


def to_lists(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.all():
        jt = pref.job_type
        ro = pref.remote_option
        new_jt = json.dumps([jt]) if jt else json.dumps([])
        new_ro = json.dumps([ro]) if ro else json.dumps([])
        Preference.objects.filter(pk=pref.pk).update(
            job_type=new_jt, remote_option=new_ro
        )


def to_strings(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.all():
        jt = pref.job_type or []
        ro = pref.remote_option or []
        Preference.objects.filter(pk=pref.pk).update(
            job_type=(jt[0] if jt else None),
            remote_option=(ro[0] if ro else None),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0013_profile_whitelist"),
    ]

    operations = [
        migrations.RunPython(to_lists, reverse_code=to_strings),
        migrations.AlterField(
            model_name="preference",
            name="job_type",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="preference",
            name="remote_option",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
