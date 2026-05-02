from django.contrib import admin

from billing.models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "preference_limit", "is_active", "created_on")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "plan",
        "status",
        "started_at",
        "expires_at",
        "payment_provider",
        "created_on",
    )
    list_filter = ("status", "payment_provider")
    search_fields = ("profile__full_name", "profile__user__email", "payment_ref")
    autocomplete_fields = ("profile", "plan")
    readonly_fields = ("payment_ref", "payment_link", "created_on", "updated_on")
