"""Skill Map: the most-requested skills per job title, from crawled jobs.

Only aggregate counts leave this module. Never expose postings, companies
or JobPosting schema on the public pages (Himalayas' terms forbid passing
its jobs on, and the pages are meant to show the market, not a job list).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.utils import timezone

from jobs.consts import JobType, RemoteOption
from jobs.models import Job, SkillMapPage, SkillMapSnapshot
from jobs.scrapers.filters import title_words

WINDOW_DAYS = 90
TOP_HARD = 15
TOP_SOFT = 8

# Casefolded spelling -> casefolded canonical key. The page shows the most
# common original spelling inside each group.
SKILL_ALIASES = {
    "ms excel": "excel",
    "microsoft excel": "excel",
    "ms office": "microsoft office",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "vuejs": "vue.js",
    "vue": "vue.js",
    "postgres": "postgresql",
    "golang": "go",
    "js": "javascript",
    "ts": "typescript",
}

_MONTHS_ID = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
)


def format_date_id(d: date) -> str:
    """'1 Agu 2026' — Indonesian short month, whatever LANGUAGE_CODE says."""
    return f"{d.day} {_MONTHS_ID[d.month - 1]} {d.year}"


def skill_key(skill: str) -> str:
    key = " ".join(str(skill).split()).casefold()
    return SKILL_ALIASES.get(key, key)


def title_matches(title: str, words: list[str], excluded: list[str]) -> bool:
    """Each word must start a word in the title ("analyst" matches "Analysts",
    "ui" does not match "Build"); any excluded word drops it."""
    t = title.lower()

    def has(w: str) -> bool:
        return re.search(rf"\b{re.escape(w)}", t) is not None

    return all(has(w) for w in words) and not any(has(w) for w in excluded)


def matching_jobs(page: SkillMapPage, since) -> list[dict]:
    words = title_words(page.match_words or page.title)
    if not words:
        return []
    excluded = title_words(page.exclude_words)
    qs = Job.objects.filter(created_on__gte=since).exclude(hard_skills=[])
    # icontains narrows in SQL; title_matches applies the stricter rule.
    for w in words:
        qs = qs.filter(title__icontains=w)
    rows = qs.values(
        "title", "company", "hard_skills", "soft_skills", "remote_option", "job_type"
    )
    jobs, seen = [], set()
    for row in rows:
        if not title_matches(row["title"], words, excluded):
            continue
        # The same posting often arrives from two boards; count it once.
        if row["company"]:
            dedup = (row["company"].casefold().strip(), row["title"].casefold().strip())
            if dedup in seen:
                continue
            seen.add(dedup)
        jobs.append(row)
    return jobs


def _rank(skill_lists, total: int, top: int) -> list[dict]:
    counts: Counter = Counter()
    spellings: dict[str, Counter] = defaultdict(Counter)
    for skills in skill_lists:
        keys = set()
        for s in skills if isinstance(skills, list) else []:
            if not isinstance(s, str) or not s.strip():
                continue
            k = skill_key(s)
            spellings[k][" ".join(s.split())] += 1
            keys.add(k)
        counts.update(keys)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return [
        {
            "name": spellings[k].most_common(1)[0][0],
            "count": c,
            "pct": round(100 * c / total) if total else 0,
        }
        for k, c in ranked
    ]


def _share(values, choices, total: int) -> list[dict]:
    counts = Counter(v for v in values if v)
    return [
        {
            "value": value,
            "label": label,
            "count": counts[value],
            "pct": round(100 * counts[value] / total) if total else 0,
        }
        for value, label in choices
        if counts[value]
    ]


def compute_snapshot(
    page: SkillMapPage, *, window_days: int = WINDOW_DAYS, now=None
) -> dict:
    now = now or timezone.now()
    since = now - timedelta(days=window_days)
    jobs = matching_jobs(page, since)
    n = len(jobs)
    return {
        "window_start": timezone.localdate(since).isoformat(),
        "window_end": timezone.localdate(now).isoformat(),
        "job_count": n,
        "hard_skills": _rank((j["hard_skills"] for j in jobs), n, TOP_HARD),
        "soft_skills": _rank((j["soft_skills"] for j in jobs), n, TOP_SOFT),
        "remote_options": _share(
            (j["remote_option"] for j in jobs), RemoteOption.choices, n
        ),
        "job_types": _share((j["job_type"] for j in jobs), JobType.choices, n),
    }


def refresh_page(
    page: SkillMapPage, *, window_days: int = WINDOW_DAYS
) -> SkillMapSnapshot:
    data = compute_snapshot(page, window_days=window_days)
    snap, _ = SkillMapSnapshot.objects.update_or_create(
        page=page,
        computed_on=timezone.localdate(),
        defaults={
            "window_days": window_days,
            "job_count": data["job_count"],
            "data": data,
        },
    )
    return snap


def visible_snapshot(page: SkillMapPage) -> SkillMapSnapshot | None:
    """The snapshot to show, or None while the page is unpublished or thin."""
    if not page.is_published:
        return None
    snap = page.latest_snapshot()
    if snap is None or snap.job_count < page.min_jobs:
        return None
    return snap


def visible_pages() -> list[tuple[SkillMapPage, SkillMapSnapshot]]:
    pages = SkillMapPage.objects.filter(is_published=True).prefetch_related("snapshots")
    out = []
    for page in pages:
        snaps = sorted(
            page.snapshots.all(),
            key=lambda s: (s.computed_on, s.created_on),
            reverse=True,
        )
        if snaps and snaps[0].job_count >= page.min_jobs:
            out.append((page, snaps[0]))
    return out
