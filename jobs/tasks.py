import logging
import time
from itertools import islice

from celery import shared_task
from django.utils import timezone

from core.notifications.discord import send_discord_message
from jobs.models import CrawlHealthTarget
from jobs.scrapers import indeed, jobstreet, linkedin

logger = logging.getLogger(__name__)

TEST_LIMIT = 5
TEST_SLEEP = 0.1

SCRAPERS = {
    CrawlHealthTarget.SOURCE_INDEED: indeed.crawl,
    CrawlHealthTarget.SOURCE_JOBSTREET: jobstreet.crawl,
    CrawlHealthTarget.SOURCE_LINKEDIN: linkedin.crawl,
}


def _probe(label, scraper, url):
    start = time.perf_counter()
    error = None
    count = 0
    try:
        items = list(
            islice(
                scraper(url, max_pages=1, sleep=TEST_SLEEP, limit=TEST_LIMIT),
                TEST_LIMIT,
            )
        )
        count = len(items)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("health probe %s raised", label)
    elapsed = time.perf_counter() - start
    return {
        "source": label,
        "url": url,
        "ok": error is None and count > 0,
        "count": count,
        "elapsed_s": round(elapsed, 1),
        "error": error,
    }


def _format_report(results):
    stamp = timezone.localtime().strftime("%Y-%m-%d %H:%M %Z")
    lines = [f"**Crawler health check — {stamp}**"]
    for r in results:
        mark = "✅" if r["ok"] else "❌"
        tail = f" ({r['error']})" if r["error"] else ""
        lines.append(
            f"{mark} {r['source']} — {r['count']} jobs in {r['elapsed_s']}s{tail}"
        )
    return "\n".join(lines)


@shared_task
def crawl_health_check() -> dict:
    """Probe each active CrawlHealthTarget, ping Discord with the result."""
    targets = list(CrawlHealthTarget.objects.filter(is_active=True))
    if not targets:
        send_discord_message("**Crawler health check** — no active targets configured.")
        return {"results": []}

    results = []
    for t in targets:
        scraper = SCRAPERS.get(t.source)
        if scraper is None:
            results.append(
                {
                    "source": t.label,
                    "url": t.url,
                    "ok": False,
                    "count": 0,
                    "elapsed_s": 0.0,
                    "error": f"unknown source: {t.source}",
                }
            )
            continue
        results.append(_probe(t.label, scraper, t.url))

    send_discord_message(_format_report(results))
    return {"results": results}
