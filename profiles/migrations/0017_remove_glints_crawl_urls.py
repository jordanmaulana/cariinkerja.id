from django.db import migrations


def drop_glints_urls(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.all():
        urls = pref.crawl_urls or []
        kept = [u for u in urls if "glints" not in (u or "").lower()]
        if kept != urls:
            pref.crawl_urls = kept
            pref.save(update_fields=["crawl_urls"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0016_preference_profiles_pr_status_2bc3c9_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(drop_glints_urls, migrations.RunPython.noop),
    ]
