from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from assessment.models import Assessment
from assessment.services import assess, check_relevance
from billing.models import SubscriptionStatus
from jobs.models import Job
from jobs.scrapers import indeed, jobstreet
from profiles.consts import Source, Status
from profiles.models import Preference

logger = logging.getLogger(__name__)

SCRAPERS = {
    Source.INDEED: indeed,
    Source.JOBSTREET: jobstreet,
}


@shared_task
def crawl_running_preferences():
    now = timezone.now()
    qs = (
        Preference.objects.filter(
            status=Status.RUNNING,
            profile__subscriptions__status=SubscriptionStatus.ACTIVE,
            profile__subscriptions__expires_at__gt=now,
        )
        .exclude(crawl_url__isnull=True)
        .exclude(crawl_url="")
        .exclude(crawl_source__isnull=True)
        .exclude(crawl_source="")
        .values_list("id", flat=True)
        .distinct()
    )
    ids = list(qs)
    logger.info("crawl_running_preferences: %d preference(s) queued", len(ids))
    for pid in ids:
        crawl_and_assess_preference.delay(pid)
    return len(ids)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_free_crawl(preference_id: str):
    """One-shot free crawl + assess. Flips status to WAITING_PAYMENT after."""
    crawl_and_assess_preference(preference_id)
    Preference.objects.filter(id=preference_id).update(
        status=Status.WAITING_PAYMENT, updated_on=timezone.now()
    )
    logger.info(
        "run_free_crawl: preference=%s flipped to WAITING_PAYMENT", preference_id
    )


@shared_task
def crawl_and_assess_preference(preference_id: str):
    pref = Preference.objects.select_related("profile").get(id=preference_id)
    scraper = SCRAPERS.get(pref.crawl_source)
    if scraper is None:
        logger.warning(
            "preference %s has unknown crawl_source %r", pref.id, pref.crawl_source
        )
        return 0

    count = 0
    for posting in scraper.crawl(pref.crawl_url):
        try:
            with transaction.atomic():
                job, _ = Job.objects.update_or_create(
                    url=posting["url"],
                    defaults={
                        "title": posting["title"],
                        "company": posting.get("company"),
                        "description": posting["description"],
                        "location": posting["location"],
                        "job_type": posting["job_type"],
                        "remote_option": posting["remote_option"],
                        "source": pref.crawl_source,
                    },
                )
        except Exception:
            logger.exception("persist failed for %s", posting.get("url"))
            continue
        assess_job.delay(job.id, pref.id)
        count += 1
    return count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def assess_job(job_id: str, preference_id: str):
    if Assessment.objects.filter(job_id=job_id, preference_id=preference_id).exists():
        return "skipped"
    job = Job.objects.get(id=job_id)
    pref = Preference.objects.select_related("profile").get(id=preference_id)

    relevance = check_relevance(job, pref)
    if not relevance.is_relevant:
        Assessment.objects.get_or_create(
            job=job,
            preference=pref,
            defaults={
                "is_relevant": False,
                "score": 0,
                "verdict": f"Filtered as irrelevant: {relevance.reason}",
            },
        )
        return "irrelevant"

    result = assess(job, pref)
    _, created = Assessment.objects.get_or_create(
        job=job,
        preference=pref,
        defaults={
            "soft_skill_match": result.soft_skill_match,
            "soft_skill_gap": result.soft_skill_gap,
            "hard_skill_match": result.hard_skill_match,
            "hard_skill_gap": result.hard_skill_gap,
            "score": result.score,
            "verdict": result.verdict,
        },
    )
    return "created" if created else "skipped"


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def reassess_assessment(assessment_id: str):
    assessment = Assessment.objects.select_related("job", "preference__profile").get(
        id=assessment_id
    )

    relevance = check_relevance(assessment.job, assessment.preference)
    if not relevance.is_relevant:
        assessment.is_relevant = False
        assessment.score = 0
        assessment.verdict = f"Filtered as irrelevant: {relevance.reason}"
        assessment.soft_skill_match = []
        assessment.soft_skill_gap = []
        assessment.hard_skill_match = []
        assessment.hard_skill_gap = []
        assessment.save(
            update_fields=[
                "is_relevant",
                "score",
                "verdict",
                "soft_skill_match",
                "soft_skill_gap",
                "hard_skill_match",
                "hard_skill_gap",
                "updated_on",
            ]
        )
        return "irrelevant"

    result = assess(assessment.job, assessment.preference)
    assessment.is_relevant = True
    assessment.soft_skill_match = result.soft_skill_match
    assessment.soft_skill_gap = result.soft_skill_gap
    assessment.hard_skill_match = result.hard_skill_match
    assessment.hard_skill_gap = result.hard_skill_gap
    assessment.score = result.score
    assessment.verdict = result.verdict
    assessment.save(
        update_fields=[
            "is_relevant",
            "soft_skill_match",
            "soft_skill_gap",
            "hard_skill_match",
            "hard_skill_gap",
            "score",
            "verdict",
            "updated_on",
        ]
    )
    return "reassessed"
