from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from assessment.models import Assessment
from billing.models import Subscription
from core.dashboard_cache import bust_dashboard_cache
from profiles.models import Preference, Profile


def _bust_on_commit():
    transaction.on_commit(bust_dashboard_cache)


@receiver(post_save, sender=Assessment)
@receiver(post_delete, sender=Assessment)
def _assessment_changed(sender, **kwargs):
    _bust_on_commit()


@receiver(post_save, sender=Subscription)
@receiver(post_delete, sender=Subscription)
def _subscription_changed(sender, **kwargs):
    _bust_on_commit()


@receiver(post_save, sender=Profile)
def _profile_saved(sender, instance, created, **kwargs):
    if created:
        _bust_on_commit()
        return
    update_fields = kwargs.get("update_fields") or set()
    if not update_fields or "linkedin_quality_ok" in update_fields:
        _bust_on_commit()


@receiver(post_save, sender=Preference)
def _preference_saved(sender, instance, created, **kwargs):
    if created:
        _bust_on_commit()
        return
    update_fields = kwargs.get("update_fields") or set()
    if not update_fields or "status" in update_fields:
        _bust_on_commit()
