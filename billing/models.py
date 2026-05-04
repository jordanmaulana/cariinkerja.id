from django.db import models

from core.models import BaseModel

OPEN_TO_WORK_DISCOUNT_PRICE = 49000


def effective_price(plan, profile, cheapest_id=None):
    if profile is None or not profile.linkedin_discount_eligible:
        return plan.price
    if cheapest_id is None:
        cheapest_id = (
            Plan.objects.filter(is_active=True)
            .order_by("price")
            .values_list("id", flat=True)
            .first()
        )
    if plan.id != cheapest_id:
        return plan.price
    if plan.price <= OPEN_TO_WORK_DISCOUNT_PRICE:
        return plan.price
    return OPEN_TO_WORK_DISCOUNT_PRICE


class Plan(BaseModel):
    name = models.CharField(max_length=80)
    price = models.PositiveIntegerField(help_text="IDR, no decimals")
    preference_limit = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "billing"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} (Rp {self.price:,})"


class SubscriptionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"
    REPLACED = "REPLACED", "Replaced"


class Subscription(BaseModel):
    profile = models.ForeignKey(
        "profiles.Profile",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    payment_provider = models.CharField(max_length=16, default="mayar")
    payment_ref = models.CharField(max_length=128, blank=True, default="")
    payment_link = models.URLField(blank=True, default="")
    amount_paid = models.PositiveIntegerField(
        default=0, help_text="IDR actually paid (post-discount, post-credit)"
    )
    replaces = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaced_by_subs",
        help_text="Old subscription this upgrade replaces.",
    )

    class Meta:
        app_label = "billing"
        indexes = [
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["payment_ref"]),
        ]

    def __str__(self):
        return f"{self.profile_id} → {self.plan_id} [{self.status}]"
