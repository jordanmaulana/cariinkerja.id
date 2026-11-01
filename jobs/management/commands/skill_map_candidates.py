"""List the job titles users search most, with how many skill-tagged jobs
match each one. With --create, also make a Skill Map page for every title
that has enough jobs (✓), publish it and build its first snapshot.

Example:

    uv run manage.py skill_map_candidates
    uv run manage.py skill_map_candidates --create
    uv run manage.py skill_map_candidates --create --draft --min-jobs 20
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from jobs.models import SkillMapPage
from jobs.skill_map import WINDOW_DAYS, matching_jobs, refresh_page
from profiles.models import Preference

TITLE_MAX = SkillMapPage._meta.get_field("title").max_length
SLUG_MAX = SkillMapPage._meta.get_field("slug").max_length


def _display_title(spellings: Counter) -> str:
    # Most common spelling; on a tie prefer one with capitals ("Data Analyst"
    # over "data analyst").
    return max(spellings.items(), key=lambda kv: (kv[1], kv[0] != kv[0].lower()))[0]


class Command(BaseCommand):
    help = "Most-searched Preference titles and their matching job counts."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=40)
        parser.add_argument("--min-jobs", type=int, default=30)
        parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
        parser.add_argument(
            "--create",
            action="store_true",
            help="create, publish and snapshot a page for every ✓ title "
            "that has no page yet",
        )
        parser.add_argument(
            "--draft",
            action="store_true",
            help="with --create: leave new pages unpublished for review in admin",
        )

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
        created = 0
        self.stdout.write(f"{'searches':>8}  {'jobs':>5}  ok  title  [slug]")
        for key, n_prefs in counts.most_common(opts["limit"]):
            title = _display_title(spellings[key])
            n_jobs = len(matching_jobs(SkillMapPage(title=title), since))
            slug = slugify(title)[:SLUG_MAX].strip("-")
            ok = n_jobs >= opts["min_jobs"]
            if slug in existing:
                tag = " (page exists)"
            elif opts["create"] and ok and slug and len(title) <= TITLE_MAX:
                page = SkillMapPage.objects.create(
                    slug=slug,
                    title=title,
                    is_published=not opts["draft"],
                    min_jobs=opts["min_jobs"],
                )
                refresh_page(page, window_days=opts["window_days"])
                existing.add(slug)
                created += 1
                tag = " (created, draft)" if opts["draft"] else " (created, live)"
            else:
                tag = ""
            self.stdout.write(
                f"{n_prefs:>8}  {n_jobs:>5}  {'✓' if ok else ' '}   {title}  [{slug}]{tag}"
            )
        if opts["create"]:
            self.stdout.write(self.style.SUCCESS(f"created {created} page(s)"))
