import logging

from celery import shared_task
from django.conf import settings
from django.urls import reverse

from core.notifications.discord import send_discord_message
from core.realtime import publish, user_channel

logger = logging.getLogger(__name__)


@shared_task
def notify_preference_created(preference_id: str) -> None:
    from profiles.models import Preference

    pref = (
        Preference.objects.select_related("profile", "profile__user")
        .filter(id=preference_id)
        .first()
    )
    if not pref:
        return
    profile = pref.profile
    name = profile.full_name or (profile.user.email if profile.user_id else "unknown")
    admin_path = reverse("preference_detail", args=[pref.id])
    admin_url = f"{settings.SITE_URL}{admin_path}"
    lines = [
        "**New Preference created**",
        f"Profile: {name}",
        f"Title: {pref.title or '-'}",
        f"URLs: {len(pref.crawl_urls)}",
        f"Status: {pref.status}",
        f"Admin: {admin_url}",
    ]
    send_discord_message("\n".join(lines))


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def crawl_linkedin_for_profile(
    profile_id: str, preference_id: str | None = None
) -> str:
    """Ingest the profile's source: LinkedIn via Apify, or an uploaded CV.

    A CV profile has no linkedin_url; its PDF text was extracted into
    linkedin_raw at onboarding, so only the LLM clean-up runs here.
    """
    from profiles.consts import Status
    from profiles.methods import crawl_and_ingest_linkedin, ingest_raw_profile
    from profiles.models import Profile
    from profiles.services import prepare_preference_for_payment

    profile = Profile.objects.get(pk=profile_id)
    if profile.linkedin_url:
        crawl_and_ingest_linkedin(profile)
    elif profile.linkedin_raw:
        ingest_raw_profile(profile, profile.linkedin_raw)
    else:
        logger.info("profile %s has no linkedin_url or CV; skipping", profile_id)
        return "skipped_no_source"

    if profile.full_profile:
        pending = profile.preferences.filter(status=Status.WAITING_ADMIN, crawl_urls=[])
        for pref in pending:
            prepare_preference_for_payment(pref)
    if profile.user_id:
        # SPA refetches the profile (quality status) and the payment gate.
        publish(user_channel(profile.user_id), {"event": "profile.ingested"})
    return "no_status_change"
