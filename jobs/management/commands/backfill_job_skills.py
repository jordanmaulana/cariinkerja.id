"""Backfill Job.hard_skills / soft_skills for rows with empty skill lists.

Example:

    uv run manage.py backfill_job_skills          # queue to Celery
    uv run manage.py backfill_job_skills --sync   # run inline (no worker)
    uv run manage.py backfill_job_skills --source workable --since-days 90 --dry-run
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from jobs.models import Job
from jobs.tasks import extract_job_skills


class Command(BaseCommand):
    help = "Extract skills for Jobs with empty hard_skills/soft_skills."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="run inline instead of queuing to Celery",
        )
        parser.add_argument(
            "--source", help="only jobs from this source, e.g. workable"
        )
        parser.add_argument(
            "--since-days", type=int, help="only jobs created in the last N days"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="print how many jobs match (one AI call each) and stop",
        )

    def handle(self, *args, **opts):
        qs = Job.objects.filter(hard_skills=[], soft_skills=[])
        if opts["source"]:
            qs = qs.filter(source=opts["source"])
        if opts["since_days"]:
            qs = qs.filter(
                created_on__gte=timezone.now() - timedelta(days=opts["since_days"])
            )
        if opts["dry_run"]:
            self.stdout.write(f"{qs.count()} job(s) would be queued")
            return
        n = 0
        for jid in qs.values_list("id", flat=True):
            if opts["sync"]:
                extract_job_skills(jid)
            else:
                extract_job_skills.delay(jid)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"queued/ran {n} job(s)"))
