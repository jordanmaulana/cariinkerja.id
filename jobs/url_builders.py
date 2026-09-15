"""Pure URL builders for job-board crawl URLs.

Reverse-engineered from real Jobstreet listing URLs (see jobstreet-url.md).
Single-value filters slot into the path; multi-value filters and remote-only
filters use query params (`worktype`, `workarrangement`).
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote_plus, urlencode

from jobs.consts import JobType, RemoteOption

JOBSTREET_BASE = "https://id.jobstreet.com"
KALIBRR_BASE = "https://www.kalibrr.com/job-board"
KALIBRR_COUNTRY = "Indonesia"
KITALULUS_SEARCH = "https://www.kitalulus.com/lowongan"
LINKEDIN_BASE = "https://www.linkedin.com/jobs/search/"
LINKEDIN_GEOID_SEA = "91000014"
LINKEDIN_GEOID_EMEA = "91000007"
SLUG_MAX_LEN = 80

# Kitalulus `types` search-param values, keyed by our JobType. Kitalulus also
# has a FREELANCE bucket we have no equivalent for.
KITALULUS_TYPES: dict[str, str] = {
    JobType.FULL_TIME.value: "FULL_TIME",
    JobType.PART_TIME.value: "PART_TIME",
    JobType.CONTRACT.value: "CONTRACT",
    JobType.INTERNSHIP.value: "INTERNSHIP",
}

# LinkedIn search filter codes.
LINKEDIN_JT_CODE: dict[str, str] = {
    JobType.FULL_TIME.value: "F",
    JobType.PART_TIME.value: "P",
    JobType.CONTRACT.value: "C",
    JobType.INTERNSHIP.value: "I",
}

LINKEDIN_WT_CODE: dict[str, str] = {
    RemoteOption.ON_SITE.value: "1",
    RemoteOption.REMOTE.value: "2",
    RemoteOption.HYBRID.value: "3",
}

JOBSTREET_JT_SLUG: dict[str, str] = {
    JobType.FULL_TIME.value: "full-time",
    JobType.PART_TIME.value: "part-time",
    JobType.CONTRACT.value: "contract-temp",
    JobType.INTERNSHIP.value: "casual-vacation",
}

JOBSTREET_JT_ID: dict[str, int] = {
    JobType.FULL_TIME.value: 242,
    JobType.PART_TIME.value: 243,
    JobType.CONTRACT.value: 244,
    JobType.INTERNSHIP.value: 245,
}

JOBSTREET_RO_SLUG: dict[str, str] = {
    RemoteOption.ON_SITE.value: "on-site",
    RemoteOption.HYBRID.value: "hybrid",
    RemoteOption.REMOTE.value: "remote",
}

JOBSTREET_RO_ID: dict[str, int] = {
    RemoteOption.HYBRID.value: 1,
    RemoteOption.ON_SITE.value: 2,
    RemoteOption.REMOTE.value: 3,
}

# Kalibrr `/t/<slug>` path filter per JobType. PART_TIME maps to two Kalibrr
# tenures because `jobs.scrapers.kalibrr.TENURE_TO_JOBTYPE` folds "Freelance"
# into PART_TIME — filtering has to mirror the parse mapping or we would drop
# postings the scraper would have accepted.
KALIBRR_TENURE_SLUG: dict[str, tuple[str, ...]] = {
    JobType.FULL_TIME.value: ("full-time",),
    JobType.PART_TIME.value: ("part-time", "freelance"),
    JobType.CONTRACT.value: ("contractual",),
    JobType.INTERNSHIP.value: ("internship",),
}


def slugify_title(title: str) -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if len(slug) > SLUG_MAX_LEN:
        slug = slug[:SLUG_MAX_LEN].rsplit("-", 1)[0] or slug[:SLUG_MAX_LEN]
    return slug


def _dedupe_known(values: list[str] | None, known: dict[str, object]) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in known and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def build_jobstreet_url(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
) -> str | None:
    if not title or not title.strip():
        return None
    slug = slugify_title(title)
    if not slug:
        return None

    base_path = f"/{slug}-jobs"
    jts = _dedupe_known(job_types, JOBSTREET_JT_SLUG)
    ros = _dedupe_known(remote_options, JOBSTREET_RO_SLUG)

    path = base_path
    query: list[tuple[str, str]] = []

    if len(jts) >= 2:
        query.append(("worktype", ",".join(str(JOBSTREET_JT_ID[v]) for v in jts)))
        if ros:
            query.append(
                ("workarrangement", ",".join(str(JOBSTREET_RO_ID[v]) for v in ros))
            )
    elif len(jts) == 1:
        path = f"{base_path}/{JOBSTREET_JT_SLUG[jts[0]]}"
        if len(ros) >= 2:
            query.append(
                ("workarrangement", ",".join(str(JOBSTREET_RO_ID[v]) for v in ros))
            )
        elif len(ros) == 1:
            path = f"{path}/{JOBSTREET_RO_SLUG[ros[0]]}"
    else:
        if ros:
            query.append(
                ("workarrangement", ",".join(str(JOBSTREET_RO_ID[v]) for v in ros))
            )

    url = f"{JOBSTREET_BASE}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def build_linkedin_url(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
    geo_id: str = LINKEDIN_GEOID_SEA,
) -> str | None:
    """LinkedIn guest-searchable jobs URL for a Preference title.

    Region is driven by ``geo_id`` (defaults to SEA ``91000014``; pass
    ``LINKEDIN_GEOID_EMEA`` for EMEA). Job type / workplace filters slot in as
    comma-joined ``f_JT`` / ``f_WT`` query params (LinkedIn's convention). The
    scraper later strips this down to the guest endpoint, but these params
    survive the translation.
    """
    if not title or not title.strip():
        return None
    query: list[tuple[str, str]] = [
        ("keywords", title.strip()),
        ("geoId", geo_id),
    ]
    jts = _dedupe_known(job_types, LINKEDIN_JT_CODE)
    if jts:
        query.append(("f_JT", ",".join(LINKEDIN_JT_CODE[v] for v in jts)))
    ros = _dedupe_known(remote_options, LINKEDIN_WT_CODE)
    if ros:
        query.append(("f_WT", ",".join(LINKEDIN_WT_CODE[v] for v in ros)))
    return f"{LINKEDIN_BASE}?{urlencode(query, quote_via=quote_plus)}"


def build_kalibrr_url(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
) -> str | None:
    """Kalibrr search URL for a Preference, with its filters in the path.

    Kalibrr's search path is a sequence of ``/<key>/<value>`` segments. ``t`` is
    repeatable and OR-ed by the backend, so every requested job type lands in one
    URL. ``work_from_home/y`` is only appended when remote is the *sole* option
    asked for: Kalibrr can filter *to* work-from-home but never *away* from it,
    so adding it to a ``[remote, hybrid]`` preference would silently hide the
    hybrid postings. On-site is not expressible on Kalibrr at all.
    """
    if not title or not title.strip():
        return None
    slug = slugify_title(title)
    if not slug:
        return None

    url = f"{KALIBRR_BASE}/te/{slug}/co/{KALIBRR_COUNTRY}"

    # Iterate the map, not the caller's list, so the same preference always
    # regenerates a byte-identical URL.
    requested = set(job_types or ())
    for job_type, slugs in KALIBRR_TENURE_SLUG.items():
        if job_type in requested:
            url += "".join(f"/t/{s}" for s in slugs)

    ros = [r for r in dict.fromkeys(remote_options or ()) if r in RemoteOption.values]
    if ros == [RemoteOption.REMOTE.value]:
        url += "/work_from_home/y"
    return url


def build_kitalulus_url(
    title: str | None, job_types: list[str] | None = None
) -> str | None:
    """Kitalulus keyword search URL for a Preference.

    Kitalulus is a Next.js page whose search params feed a server-side GraphQL
    ``vacanciesV4`` query, so ``types`` and ``sortBy`` are already applied in
    the SSR HTML the scraper parses (verified 2026-09-09).

    ``sortBy=updatedAt`` is always sent: the default ``isHighlighted`` sort is
    promoted-first and barely moves day to day, so ``CRAWL_ITEM_LIMIT`` would be
    spent re-reading postings we already assessed. Only ``isHighlighted``,
    ``updatedAt`` and ``createdAt`` are valid — an unknown value renders a page
    with zero results, so don't make this configurable.

    ``locationSites`` is deliberately not sent: it accepts only REMOTE/ON_SITE
    (no hybrid) and REMOTE matches ~195 postings site-wide, which would starve
    the crawl. Remote mismatch stays the assessor's job.
    """
    if not title or not title.strip():
        return None
    params = [("keyword", title.strip()), ("sortBy", "updatedAt")]
    wanted = set(job_types or [])
    # Iterate the map, not the caller's list, so the URL is stable and deduped.
    mapped = [v for k, v in KITALULUS_TYPES.items() if k in wanted]
    # All four selected is a no-op filter — leave it off rather than lie.
    if mapped and len(mapped) < len(KITALULUS_TYPES):
        params += [("types", v) for v in mapped]
    return f"{KITALULUS_SEARCH}?{urlencode(params)}"


def build_crawl_urls(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
) -> list[str]:
    """Kalibrr + Kitalulus search URLs for a Preference.

    Indeed, JobStreet and LinkedIn were dropped from the generated set on
    2026-09-09 (see ``_docs/scraping-policy.md`` §3 exit condition). Their
    builders and scrapers stay so an admin can still paste such a URL by hand.
    Karirhub was removed outright on 2026-09-09 — low volume and low quality,
    not a policy problem — scraper and all.

    ``job_types`` reaches both.

    ``remote_options`` reaches Kalibrr only, and only as an all-or-nothing
    work-from-home narrowing (see ``build_kalibrr_url``). Kitalulus'
    ``locationSites`` cannot express hybrid and matches too few postings to be
    worth narrowing to. Every remaining remote mismatch is handled downstream by
    the assessor.
    """
    urls = [
        build_kalibrr_url(title, job_types, remote_options),
        build_kitalulus_url(title, job_types),
    ]
    return [u for u in urls if u]
