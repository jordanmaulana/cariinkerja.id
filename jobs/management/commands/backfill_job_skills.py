"""Backfill Job.hard_skills / soft_skills for rows with empty skill lists.

Example:

    uv run manage.py backfill_job_skills          # queue to Celery
    uv run manage.py backfill_job_skills --sync   # run inline (no worker)
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

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

    def handle(self, *args, **opts):
        qs = Job.objects.filter(hard_skills=[], soft_skills=[])
        n = 0
        for jid in qs.values_list("id", flat=True):
            if opts["sync"]:
                extract_job_skills(jid)
            else:
                extract_job_skills.delay(jid)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"queued/ran {n} job(s)"))
