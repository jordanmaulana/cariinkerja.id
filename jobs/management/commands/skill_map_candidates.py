"""List the job titles users search most, with how many skill-tagged jobs
match each one — use it to pick which Skill Map pages to create.

Example:

    uv run manage.py skill_map_candidates
    uv run manage.py skill_map_candidates --limit 60 --min-jobs 30 --window-days 90
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from jobs.models import SkillMapPage
from jobs.skill_map import WINDOW_DAYS, matching_jobs
from profiles.models import Preference


class Command(BaseCommand):
    help = "Most-searched Preference titles and their matching job counts."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=40)
        parser.add_argument("--min-jobs", type=int, default=30)
        parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)

    def handle(self, *args, **opts):
        counts: Counter = Counter()
        spellings: dict[str, Counter] = defaultdict(Counter)
        for title in Preference.objects.exclude(title__isnull=True).values_list(
            "title", flat=True
        ):
            clean = " ".join(title.split())
            if not clean:
                continue
            counts[clean.casefold()] += 1
            spellings[clean.casefold()][clean] += 1

        since = timezone.now() - timedelta(days=opts["window_days"])
        existing = set(SkillMapPage.objects.values_list("slug", flat=True))
        self.stdout.write(f"{'searches':>8}  {'jobs':>5}  ok  title  [slug]")
        for key, n_prefs in counts.most_common(opts["limit"]):
            title = spellings[key].most_common(1)[0][0]
            n_jobs = len(matching_jobs(SkillMapPage(title=title), since))
            slug = slugify(title)
            ok = "✓" if n_jobs >= opts["min_jobs"] else " "
            tag = " (page exists)" if slug in existing else ""
            self.stdout.write(
                f"{n_prefs:>8}  {n_jobs:>5}  {ok}   {title}  [{slug}]{tag}"
            )
