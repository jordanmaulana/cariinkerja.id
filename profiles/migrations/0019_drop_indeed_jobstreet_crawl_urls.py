"""Strip Indeed and JobStreet URLs from stored Preference.crawl_urls.

Both scrapers were removed on 2026-11-01. ``crawl_urls`` is stored rather than
derived, so without this every live Preference keeps two URLs that resolve to
no scraper. Matches by hostname (as ``scraper_for_url`` does) so hand-pasted
URLs on other hosts survive. A Preference left with no URL at all (one created
before LinkedIn was added) is refilled from the live builder; otherwise the
crawl gate would skip it. Idempotent.
"""

from urllib.parse import urlparse

from django.db import migrations

from jobs.url_builders import build_crawl_urls

REMOVED_HOSTS = ("indeed.com", "jobstreet.com")


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
        ("profiles", "0018_advance_waiting_admin_to_waiting_payment"),
    ]

    operations = [
        migrations.RunPython(drop_removed_urls, migrations.RunPython.noop),
    ]
