from django.db import migrations, models


def forward_copy_url_to_list(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.all():
        if pref.crawl_url:
            pref.crawl_urls = [pref.crawl_url]
            pref.save(update_fields=["crawl_urls"])


def reverse_copy_list_to_url(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.all():
        if pref.crawl_urls:
            pref.crawl_url = pref.crawl_urls[0]
            pref.save(update_fields=["crawl_url"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0014_alter_preference_job_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="preference",
            name="crawl_urls",
            field=models.JSONField(
                blank=True, default=list, help_text="Filled by Admin"
            ),
        ),
        migrations.RunPython(forward_copy_url_to_list, reverse_copy_list_to_url),
        migrations.RemoveField(
            model_name="preference",
            name="crawl_source",
        ),
        migrations.RemoveField(
            model_name="preference",
            name="crawl_url",
        ),
    ]
