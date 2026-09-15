from django.db import migrations

from jobs.url_builders import build_crawl_urls


def regenerate_crawl_urls(apps, schema_editor):
    """Karirhub search URLs moved from the landing page to the real search page
    (`/lowongan-dalam-negeri/lowongan`) and gained `jobTypes[N][id]`, the
    job-type filter the portal's vacancy API honours as `job_types[]`.
    crawl_urls is stored rather than derived, so existing preferences keep
    crawling the old keyword-only shape until rewritten. Same job as the
    /preferences/regenerate-all-urls/ admin action, run automatically on deploy.

    A no-op on a database where 0019 has not yet run — it calls the same live
    builder — and idempotent besides."""
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.exclude(crawl_urls=[]).iterator():
        urls = build_crawl_urls(pref.title, pref.job_type, pref.remote_option)
        if urls and urls != pref.crawl_urls:
            pref.crawl_urls = urls
            pref.save(update_fields=["crawl_urls", "updated_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0019_regenerate_kitalulus_crawl_urls"),
    ]

    operations = [
        migrations.RunPython(regenerate_crawl_urls, migrations.RunPython.noop),
    ]
