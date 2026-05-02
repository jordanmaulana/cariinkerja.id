from bson.objectid import ObjectId
from django.contrib.auth.models import User
from django.db import models

OPEN_TO_WORK_DISCOUNT_PRICE = 49000


def make_object_id():
    return str(ObjectId())


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


class BaseModel(models.Model):
    id = models.CharField(primary_key=True, default=make_object_id, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True
        ordering = ["id"]
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        return f"{self.id}"


class Plan(BaseModel):
    name = models.CharField(max_length=80)
    price = models.PositiveIntegerField(help_text="IDR, no decimals")
    preference_limit = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "core"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} (Rp {self.price:,})"


class SubscriptionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


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

    class Meta:
        app_label = "core"
        indexes = [
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["payment_ref"]),
        ]

    def __str__(self):
        return f"{self.profile_id} → {self.plan_id} [{self.status}]"


class AppSetting(models.Model):
    key = models.CharField()
    should_be_unique = models.BooleanField(default=True)
    str_value = models.TextField(null=True, blank=True)
    int_value = models.IntegerField(null=True, blank=True)
    float_value = models.FloatField(null=True, blank=True)
    bool_value = models.BooleanField(default=True)

    class Meta:
        app_label = "core"

    @staticmethod
    def get(key, value_type, default=None):
        if value_type not in ["str", "int", "float", "bool"]:
            raise ValueError("Value type should be one of str, int, float, or bool")

        try:
            setting = AppSetting.objects.get(key__iexact=key)
            return getattr(setting, f"{value_type}_value")
        except AppSetting.DoesNotExist:
            return default

    def __str__(self):
        return self.key
