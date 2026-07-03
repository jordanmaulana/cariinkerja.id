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
LINKEDIN_BASE = "https://www.linkedin.com/jobs/search/"
LINKEDIN_GEOID_SEA = "91000014"
LINKEDIN_GEOID_EMEA = "91000007"
SLUG_MAX_LEN = 80

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


def _slugify_title(title: str) -> str:
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
    slug = _slugify_title(title)
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


def build_crawl_urls(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
) -> list[str]:
    """Standard Indeed + JobStreet + LinkedIn listing URLs for a Preference."""
    if not title or not title.strip():
        return []
    urls = [f"https://id.indeed.com/jobs?q={quote_plus(title)}"]
    js = build_jobstreet_url(title, job_types, remote_options)
    if js:
        urls.append(js)
    li = build_linkedin_url(title, job_types, remote_options)
    if li:
        urls.append(li)
    # EMEA is only worth crawling for remote-seeking preferences (an on-site
    # EMEA role is unreachable from Indonesia); force the remote filter on it.
    if remote_options and RemoteOption.REMOTE.value in remote_options:
        emea = build_linkedin_url(
            title, job_types, [RemoteOption.REMOTE.value], geo_id=LINKEDIN_GEOID_EMEA
        )
        if emea:
            urls.append(emea)
    return urls
