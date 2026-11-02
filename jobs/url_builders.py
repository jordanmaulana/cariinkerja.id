"""Pure URL builders for job-board crawl URLs (LinkedIn + the remote API boards)."""

from __future__ import annotations

from urllib.parse import quote_plus, urlencode

from jobs.consts import JobType, RemoteOption

LINKEDIN_BASE = "https://www.linkedin.com/jobs/search/"
LINKEDIN_GEOID_SEA = "91000014"
LINKEDIN_GEOID_EMEA = "91000007"
HIMALAYAS_SEARCH = "https://himalayas.app/jobs/api/search"
JOBICY_API = "https://jobicy.com/api/jobs"
WORKABLE_SEARCH = "https://jobs.workable.com/search"

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

# Himalayas `employment_type` values (comma-joined in one param).
HIMALAYAS_EMPLOYMENT: dict[str, list[str]] = {
    JobType.FULL_TIME.value: ["Full Time"],
    JobType.PART_TIME.value: ["Part Time"],
    JobType.CONTRACT.value: ["Contractor", "Temporary"],
    JobType.INTERNSHIP.value: ["Intern"],
}


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


def build_himalayas_url(
    title: str | None,
    job_types: list[str] | None = None,
) -> str | None:
    """Himalayas search-API URL for a Preference title.

    We store the JSON API URL itself: the public site is Cloudflare-gated.
    Himalayas is remote-only, so there is no remote filter; no country filter
    either (product decision — crawl the global remote pool).
    """
    if not title or not title.strip():
        return None
    query: list[tuple[str, str]] = [("q", title.strip())]
    jts = _dedupe_known(job_types, HIMALAYAS_EMPLOYMENT)
    if jts:
        query.append(
            (
                "employment_type",
                ",".join(e for v in jts for e in HIMALAYAS_EMPLOYMENT[v]),
            )
        )
    return f"{HIMALAYAS_SEARCH}?{urlencode(query)}"


def build_jobicy_url(title: str | None) -> str | None:
    """Jobicy API URL for a Preference title.

    Jobicy is remote-only and has no job-type filter. ``geo`` takes one slug
    and there is none for Indonesia; ``apac`` also includes "Anywhere" jobs.
    ``count=20`` leaves headroom above the crawl item limit.
    """
    if not title or not title.strip():
        return None
    query = [("geo", "apac"), ("tag", title.strip()), ("count", "20")]
    return f"{JOBICY_API}?{urlencode(query)}"


def build_workable_url(title: str | None) -> str | None:
    """Workable crawl URL for a Preference title.

    Workable's human search page, so admins can click it; the scraper sends
    its ``query`` to the search API, always limited to Indonesia (that already
    includes remote jobs open to Indonesia).
    """
    if not title or not title.strip():
        return None
    query = [("query", title.strip()), ("location", "Indonesia")]
    return f"{WORKABLE_SEARCH}?{urlencode(query)}"


def build_crawl_urls(
    title: str | None,
    job_types: list[str] | None = None,
    remote_options: list[str] | None = None,
) -> list[str]:
    """Standard LinkedIn SEA (+ EMEA) + Himalayas + Jobicy + Workable URLs."""
    if not title or not title.strip():
        return []
    urls: list[str] = []
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
    # Remote-only boards, appended last for every preference, whatever
    # remote_option says.
    hm = build_himalayas_url(title, job_types)
    if hm:
        urls.append(hm)
    jc = build_jobicy_url(title)
    if jc:
        urls.append(jc)
    wk = build_workable_url(title)
    if wk:
        urls.append(wk)
    return urls
