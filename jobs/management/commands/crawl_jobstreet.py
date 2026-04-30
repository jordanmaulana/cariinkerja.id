"""Crawl a Jobstreet Indonesia listing URL and persist Job rows.

Example:

    uv run manage.py crawl_jobstreet \\
        "https://id.jobstreet.com/id/mobile-jobs/part-time/remote" \\
        --max-pages 1 --dry-run
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jobs.models import Job
from jobs.scrapers import jobstreet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Crawl a Jobstreet listing URL and upsert Job rows by url."

    def add_arguments(self, parser):
        parser.add_argument(
            "url",
            help="Jobstreet listing URL (e.g. https://id.jobstreet.com/id/mobile-jobs/part-time/remote)",
        )
        parser.add_argument("--max-pages", type=int, default=1)
        parser.add_argument("--sleep", type=float, default=jobstreet.DEFAULT_SLEEP)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and print postings without writing to the DB.",
        )

    def handle(self, *args, **opts):
        url: str = opts["url"]
        if not url.startswith("http"):
            raise CommandError(f"url must be absolute: {url!r}")

        created = updated = skipped = 0
        for posting in jobstreet.crawl(
            url,
            max_pages=opts["max_pages"],
            sleep=opts["sleep"],
            limit=opts["limit"],
        ):
            if opts["dry_run"]:
                self.stdout.write(json.dumps(posting, ensure_ascii=False))
                continue
            try:
                with transaction.atomic():
                    _, was_created = Job.objects.update_or_create(
                        url=posting["url"],
                        defaults={
                            "title": posting["title"],
                            "company": posting.get("company"),
                            "description": posting["description"],
                            "location": posting["location"],
                            "job_type": posting["job_type"],
                            "remote_option": posting["remote_option"],
                            "source": "jobstreet",
                        },
                    )
            except Exception as exc:
                skipped += 1
                logger.exception("persist failed for %s: %s", posting["url"], exc)
                continue
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"done — created={created} updated={updated} skipped={skipped}"
            )
        )
