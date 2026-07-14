from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from profiles.models import Preference
from profiles.services import prepare_preference_for_payment
from profiles.tasks import notify_preference_created


@receiver(post_save, sender=Preference)
def preference_created(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: notify_preference_created.delay(instance.id))
    prepare_preference_for_payment(instance)
