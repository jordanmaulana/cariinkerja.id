from django.urls import path

from api.v1 import (
    assessments_api,
    auth_api,
    billing_api,
    dashboard_api,
    landing_api,
    payments_api,
    preferences_api,
    profiles_api,
)

urlpatterns = [
    path("landing/stats/", landing_api.public_stats, name="api-v1-landing-stats"),
    path("auth/google/", auth_api.google, name="api-v1-auth-google"),
    path("auth/logout/", auth_api.logout, name="api-v1-logout"),
    path("auth/me/", auth_api.me, name="api-v1-me"),
    path("profile/me/", profiles_api.detail, name="api-v1-profile-me"),
    path("onboarding/", profiles_api.onboarding, name="api-v1-onboarding"),
    path("dashboard/stats/", dashboard_api.stats, name="api-v1-dashboard-stats"),
    path(
        "preferences/",
        preferences_api.list_or_create,
        name="api-v1-preference-list",
    ),
    path(
        "preferences/<str:pk>/",
        preferences_api.detail,
        name="api-v1-preference-detail",
    ),
    path("assessments/", assessments_api.list, name="api-v1-assessment-list"),
    path(
        "assessments/<str:pk>/",
        assessments_api.detail,
        name="api-v1-assessment-detail",
    ),
    path("payment-gate/", billing_api.payment_gate, name="api-v1-payment-gate"),
    path("plans/", billing_api.list, name="api-v1-plan-list"),
    path("subscriptions/me/", billing_api.detail, name="api-v1-subscription-me"),
    path(
        "subscriptions/stream/",
        billing_api.stream,
        name="api-v1-subscription-stream",
    ),
    path(
        "subscriptions/checkout/",
        billing_api.create,
        name="api-v1-subscription-checkout",
    ),
    path(
        "subscriptions/upgrade-quote/",
        billing_api.upgrade_quote,
        name="api-v1-subscription-upgrade-quote",
    ),
    path(
        "subscriptions/cancel-pending/",
        billing_api.cancel_pending,
        name="api-v1-subscription-cancel-pending",
    ),
    path(
        "subscriptions/<str:pk>/recheck/",
        billing_api.recheck,
        name="api-v1-subscription-recheck",
    ),
    path("payments/mayar/webhook/", payments_api.webhook, name="api-v1-mayar-webhook"),
]
