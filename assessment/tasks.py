from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, time
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from assessment.services import assess, check_relevance
from billing.models import SubscriptionStatus
from core.notifications.email import send_email
from jobs.models import Job
from jobs.scrapers import scraper_for_url
from profiles.consts import Status
from profiles.models import Preference

JKT = ZoneInfo("Asia/Jakarta")
HIGH_SCORE_THRESHOLD = 80

logger = logging.getLogger(__name__)


@shared_task
def crawl_running_preferences():
    now = timezone.now()
    eligible = Q(
        profile__subscriptions__status=SubscriptionStatus.ACTIVE,
        profile__subscriptions__expires_at__gt=now,
    ) | Q(profile__whitelist=True)
    qs = (
        Preference.objects.filter(eligible, status=Status.RUNNING)
        .exclude(crawl_urls=[])
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
    count = 0
    for url in pref.crawl_urls or []:
        scraper, source = scraper_for_url(url)
        if scraper is None:
            logger.warning("preference %s has unknown crawl_url %r", pref.id, url)
            continue
        try:
            for posting in scraper.crawl(url):
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
                                "source": source,
                            },
                        )
                except Exception:
                    logger.exception("persist failed for %s", posting.get("url"))
                    continue
                assess_job.delay(job.id, pref.id)
                count += 1
        except Exception:
            logger.exception("crawl failed for preference=%s url=%s", pref.id, url)
            continue
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


def _today_start_jkt() -> datetime:
    now_jkt = timezone.now().astimezone(JKT)
    return datetime.combine(now_jkt.date(), time.min, tzinfo=JKT)


@shared_task
def email_morning_high_score_summary():
    today_start = _today_start_jkt()

    qs = Assessment.objects.filter(
        status=AssessmentStatus.NEW,
        score__gte=HIGH_SCORE_THRESHOLD,
        created_on__gte=today_start,
        is_relevant=True,
    ).select_related("preference__profile__user")

    counts: dict[str, int] = defaultdict(int)
    profile_email: dict[str, str] = {}

    for a in qs.iterator():
        profile = a.preference.profile
        if profile is None or profile.user_id is None:
            continue
        email = (profile.user.email or "").strip()
        if not email:
            continue
        counts[str(profile.id)] += 1
        profile_email.setdefault(str(profile.id), email)

    base = settings.FRONTEND_URL.rstrip("/")
    link = f"{base}/assessments/?status=new&min_score={HIGH_SCORE_THRESHOLD}"

    sent = 0
    for pid, n in counts.items():
        recipient = profile_email[pid]
        subject = f"Ada {n} loker skor tinggi buat kamu hari ini"
        body = (
            "Halo!\n\n"
            f"Hari ini ada {n} loker dengan skor kecocokan {HIGH_SCORE_THRESHOLD}+ "
            "yang baru masuk antreanmu.\n\n"
            f"Cek di sini: {link}\n\n"
            "— Tim cariinkerja.id"
        )
        html_body = (
            "<p>Halo!</p>"
            f"<p>Hari ini ada <strong>{n} loker</strong> dengan skor kecocokan "
            f"<strong>{HIGH_SCORE_THRESHOLD}+</strong> yang baru masuk antreanmu.</p>"
            f'<p><a href="{link}">Lihat loker skor tinggi</a></p>'
            "<p>— Tim cariinkerja.id</p>"
        )
        try:
            send_email(
                subject=subject,
                to=[recipient],
                body=body,
                html_body=html_body,
                from_name="cariinkerja.id",
            )
            sent += 1
        except Exception:
            logger.exception("morning email failed for profile=%s", pid)

    logger.info("email_morning_high_score_summary: %d email(s) sent", sent)
    return sent
