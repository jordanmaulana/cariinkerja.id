from django.db import migrations

from jobs.url_builders import build_crawl_urls


def regenerate_crawl_urls(apps, schema_editor):
    """Kitalulus search URLs gained `types` (job-type filter) and
    `sortBy=updatedAt` (freshest-first instead of promoted-first); Kalibrr URLs
    gained `/t/<tenure>` and `/work_from_home/y` path filters. crawl_urls is
    stored rather than derived, so existing preferences keep crawling the old
    shape until rewritten. Same job as the /preferences/regenerate-all-urls/
    admin action, run automatically on deploy."""
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.exclude(crawl_urls=[]).iterator():
        urls = build_crawl_urls(pref.title, pref.job_type, pref.remote_option)
        if urls and urls != pref.crawl_urls:
            pref.crawl_urls = urls
            pref.save(update_fields=["crawl_urls", "updated_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0018_advance_waiting_admin_to_waiting_payment"),
    ]

    operations = [
        migrations.RunPython(regenerate_crawl_urls, migrations.RunPython.noop),
    ]
