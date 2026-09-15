"""Strip Karirhub URLs from stored Preference.crawl_urls.

Karirhub was removed outright on 2026-09-09 — low volume and low quality, so its
scraper, command, hostname branch and URL builder are all gone. ``crawl_urls`` is
stored rather than derived, so without this every live Preference keeps a URL
that now resolves to no scraper at all.

Filters by hostname rather than calling ``build_crawl_urls`` the way 0019/0020
do: importing the live builder makes an already-applied migration's behaviour
drift whenever the builder changes, and a blanket regenerate also discards any
URL a superuser pasted by hand. Idempotent.
"""

from django.db import migrations

KARIRHUB_HOST = "karirhub.kemnaker.go.id"


def drop_karirhub(apps, schema_editor):
    Preference = apps.get_model("profiles", "Preference")
    for pref in Preference.objects.exclude(crawl_urls=[]).iterator():
        kept = [u for u in pref.crawl_urls if KARIRHUB_HOST not in u]
        if kept != pref.crawl_urls:
            pref.crawl_urls = kept
            pref.save(update_fields=["crawl_urls", "updated_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0020_regenerate_karirhub_crawl_urls"),
    ]

    operations = [
        migrations.RunPython(drop_karirhub, migrations.RunPython.noop),
    ]
