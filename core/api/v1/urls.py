from django.urls import path

from core.api.v1.views import (
    assessment_detail,
    assessment_list,
    cancel_pending,
    checkout,
    dashboard_stats,
    google_auth,
    logout,
    mayar_webhook,
    me,
    my_subscription,
    onboarding,
    payment_gate,
    plan_list,
    preference_detail,
    preference_list,
    profile_me,
    subscription_recheck,
    subscription_stream,
    upgrade_quote,
)

urlpatterns = [
    path("auth/google/", google_auth, name="api-v1-auth-google"),
    path("auth/logout/", logout, name="api-v1-logout"),
    path("auth/me/", me, name="api-v1-me"),
    path("profile/me/", profile_me, name="api-v1-profile-me"),
    path("onboarding/", onboarding, name="api-v1-onboarding"),
    path("dashboard/stats/", dashboard_stats, name="api-v1-dashboard-stats"),
    path("preferences/", preference_list, name="api-v1-preference-list"),
    path("preferences/<str:pk>/", preference_detail, name="api-v1-preference-detail"),
    path("assessments/", assessment_list, name="api-v1-assessment-list"),
    path("assessments/<str:pk>/", assessment_detail, name="api-v1-assessment-detail"),
    path("payment-gate/", payment_gate, name="api-v1-payment-gate"),
    path("plans/", plan_list, name="api-v1-plan-list"),
    path("subscriptions/me/", my_subscription, name="api-v1-subscription-me"),
    path(
        "subscriptions/stream/", subscription_stream, name="api-v1-subscription-stream"
    ),
    path("subscriptions/checkout/", checkout, name="api-v1-subscription-checkout"),
    path(
        "subscriptions/upgrade-quote/",
        upgrade_quote,
        name="api-v1-subscription-upgrade-quote",
    ),
    path(
        "subscriptions/cancel-pending/",
        cancel_pending,
        name="api-v1-subscription-cancel-pending",
    ),
    path(
        "subscriptions/<str:pk>/recheck/",
        subscription_recheck,
        name="api-v1-subscription-recheck",
    ),
    path("payments/mayar/webhook/", mayar_webhook, name="api-v1-mayar-webhook"),
]
