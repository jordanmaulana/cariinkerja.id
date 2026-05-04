from celery import shared_task
from django.conf import settings
from django.urls import reverse

from core.notifications.discord import send_discord_message


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
    admin_path = reverse("admin:profiles_preference_change", args=[pref.id])
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
