import logging

from celery import shared_task
from django.conf import settings
from django.urls import reverse

from core.notifications.discord import send_discord_message

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
        f"Source: {pref.crawl_source or '-'}",
        f"Status: {pref.status}",
        f"Admin: {admin_url}",
    ]
    send_discord_message("\n".join(lines))


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def crawl_linkedin_for_profile(profile_id: str, preference_id: str) -> str:
    from profiles.consts import Status
    from profiles.methods import crawl_and_ingest_linkedin
    from profiles.models import Preference, Profile

    profile = Profile.objects.get(pk=profile_id)
    if not profile.linkedin_url:
        logger.info("profile %s has no linkedin_url; skipping crawl", profile_id)
        return "skipped_no_url"

    crawl_and_ingest_linkedin(profile)
    return "no_status_change"
