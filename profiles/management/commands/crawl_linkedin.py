"""Run the Apify LinkedIn scraper for a Profile and persist the result.

Example:

    uv run manage.py crawl_linkedin <profile_id>
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from profiles.methods import crawl_and_ingest_linkedin
from profiles.models import Profile


class Command(BaseCommand):
    help = "Crawl LinkedIn via Apify for a Profile and run ingest_linkedin."

    def add_arguments(self, parser):
        parser.add_argument("profile_id", help="Profile primary key")

    def handle(self, *args, **opts):
        try:
            profile = Profile.objects.get(pk=opts["profile_id"])
        except Profile.DoesNotExist as exc:
            raise CommandError(f"Profile {opts['profile_id']!r} not found") from exc

        if not profile.linkedin_url:
            raise CommandError(f"Profile {profile.pk} has no linkedin_url")

        result = crawl_and_ingest_linkedin(profile)
        if result is None:
            self.stdout.write(self.style.WARNING("apify returned no items"))
            return

        raw_preview = (profile.linkedin_raw or "")[:200].replace("\n", " ⏎ ")
        self.stdout.write(
            self.style.SUCCESS(
                "done — "
                f"open_to_work={result.open_to_work} "
                f"is_sparse={result.is_sparse} "
                f"cleaned_len={len(result.cleaned_full_profile or '')} "
                f"raw_len={len(profile.linkedin_raw or '')}"
            )
        )
        self.stdout.write(f"raw[:200]: {raw_preview}")
