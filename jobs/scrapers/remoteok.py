"""JSON-API scraper for Remote OK (remoteok.com), a remote-only job board.

``https://remoteok.com/api`` returns one JSON list: item 0 is a legal notice,
the rest are the ~100 newest jobs with full HTML descriptions. There is no
pagination and no free-text search. ``?tag=`` only takes one-word tags and
spam listings carry dozens of tags, so it is useless for matching. Instead the
stored crawl URL carries our own ``search`` param
(``https://remoteok.com/api?search=<title>``), and ``crawl`` fetches the plain
feed and keeps jobs whose title contains every search word.

API terms (the ``legal`` field): link back to the job's URL on Remote OK
(followed, no ``nofollow``) and name Remote OK as the source — the SPA shows
"via Remote OK" and ``Job.url`` is the feed ``url`` unchanged. No logo
without written permission.
"""

from __future__ import annotations

import html
import logging
from typing import Iterator
from urllib.parse import parse_qsl, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from jobs.consts import RemoteOption
from jobs.scrapers.dealls import _request_json, build_client
from jobs.scrapers.filters import is_blocked_company, title_words

logger = logging.getLogger(__name__)

FEED_URL = "https://remoteok.com/api"
DEFAULT_SLEEP = 1.5


def parse_job(job: dict) -> dict | None:
    """Map one API job object to a Job-shaped dict; None if unusable."""
    url = job.get("url")
    title = html.unescape(job.get("position") or "").strip()
    raw = job.get("description") or ""
    description = BeautifulSoup(raw, "lxml").get_text("\n", strip=True) if raw else ""
    if not url or not title or not description:
        logger.warning("job missing url/title/description: id=%s", job.get("id"))
        return None
    company = html.unescape(job.get("company") or "").strip()
    # Blank stays None: the relevance gate reads a remote job's location as an
    # applicant restriction, so "Anywhere" would be a false claim.
    location = (job.get("location") or "").strip()
    return {
        "url": url,
        "title": title[:255],
        "company": company[:255] or None,
        "description": description,
        "location": location[:255] or None,
        "job_type": None,  # the feed has no job type field
        "remote_option": RemoteOption.REMOTE,
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield feed jobs whose title contains every word of the URL's ``search``.

    One request per call. ``max_pages`` / ``sleep`` are accepted for the
    shared scraper signature and ignored (the feed has one page).

    Example usage:
    https://remoteok.com/api?search=software+engineer
    """
    query = dict(parse_qsl(urlparse(url).query)).get("search", "")
    words = title_words(query)
    if not words:
        logger.warning("no search in remoteok crawl url: %s", url)
        return
    # ponytail: every running preference downloads the same ~660 KB feed per
    # crawl pass. Fine at today's scale; fetch once per pass and share it
    # (cache or a sync task) if preferences grow into the hundreds.
    owns_client = client is None
    client = client or build_client()
    try:
        try:
            feed = _request_json(client, FEED_URL)
        except Exception as exc:
            logger.error("feed fetch failed: %s", exc)
            return
        seen: set = set()
        yielded = 0
        for job in feed if isinstance(feed, list) else []:
            if limit is not None and yielded >= limit:
                return
            # Item 0 is the legal notice, which has no id.
            if not isinstance(job, dict) or not job.get("id") or job["id"] in seen:
                continue
            seen.add(job["id"])
            # ponytail: every title word must appear, no synonyms (same rule
            # as workable.crawl). Move to fuzzier matching if recall is poor.
            title = html.unescape(job.get("position") or "").lower()
            if not all(w in title for w in words):
                continue
            parsed = parse_job(job)
            if parsed is None or is_blocked_company(parsed["company"]):
                continue
            yielded += 1
            yield parsed
    finally:
        if owns_client:
            client.close()
