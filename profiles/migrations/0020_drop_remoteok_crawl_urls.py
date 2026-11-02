"""Strip Remote OK URLs from stored Preference.crawl_urls.

The Remote OK scraper was removed on 2026-11-02 (its job pages make the
applicant pay before applying). Same approach as 0019: ``crawl_urls`` is
stored rather than derived, so every live Preference would keep a URL that
resolves to no scraper. Matches by hostname (as ``scraper_for_url`` does); a
Preference left with no URL is refilled from the live builder. Idempotent.
"""

from urllib.parse import urlparse

from django.db import migrations

from jobs.url_builders import build_crawl_urls

REMOVED_HOSTS = ("remoteok.com",)


def _is_removed(url):
    try:
        host = (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return False
    return any(host == h or host.endswith(f".{h}") for h in REMOVED_HOSTS)


def drop_removed_urls(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.exclude(crawl_urls=[]).iterator():
        urls = pref.crawl_urls or []
        kept = [u for u in urls if not _is_removed(u)]
        if kept == urls:
            continue
        pref.crawl_urls = kept or build_crawl_urls(
            pref.title, pref.job_type, pref.remote_option
        )
        pref.save(update_fields=["crawl_urls", "updated_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0019_drop_indeed_jobstreet_crawl_urls"),
    ]

    operations = [
        migrations.RunPython(drop_removed_urls, migrations.RunPython.noop),
    ]
