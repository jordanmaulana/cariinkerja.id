"""Append a derived Jobstreet URL to existing Preferences that only have an
Indeed crawl URL.

One-shot — run after deploying the Jobstreet-URL builder, then leave the
file checked in (or delete in a follow-up commit).

Usage:
    uv run manage.py backfill_jobstreet_urls --dry-run
    uv run manage.py backfill_jobstreet_urls
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import transaction

from jobs.url_builders import build_jobstreet_url
from profiles.models import Preference


def _hosts(urls: list[str]) -> list[str]:
    out = []
    for u in urls or []:
        try:
            host = urlparse(u).hostname or ""
        except ValueError:
            host = ""
        out.append(host.lower())
    return out


class Command(BaseCommand):
    help = "Append derived Jobstreet URLs to Preferences that lack one."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry_run: bool = opts["dry_run"]
        updated = skipped = 0

        qs = Preference.objects.exclude(title__isnull=True).exclude(title="")
        for pref in qs.iterator():
            hosts = _hosts(pref.crawl_urls)
            if any(h.endswith("jobstreet.com") for h in hosts):
                skipped += 1
                continue
            js_url = build_jobstreet_url(pref.title, pref.job_type, pref.remote_option)
            if not js_url:
                skipped += 1
                continue

            self.stdout.write(f"preference={pref.id} append {js_url}")
            if dry_run:
                continue
            with transaction.atomic():
                pref.crawl_urls = [*(pref.crawl_urls or []), js_url]
                pref.save(update_fields=["crawl_urls", "updated_on"])
            updated += 1

        verb = "would update" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(f"done — {verb}={updated} skipped={skipped}")
        )
