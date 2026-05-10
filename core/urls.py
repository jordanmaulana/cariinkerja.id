"""URL configuration for core project."""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import (
    AdminLoginView,
    DashboardView,
    PlanCreateView,
    PlanDeleteView,
    PlanListView,
    PlanUpdateView,
    PreferenceCrawlNowView,
    PreferenceDetailView,
    PreferenceListView,
    SmtpTestView,
    SubscriptionDetailView,
    SubscriptionListView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", AdminLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "preferences/",
        PreferenceListView.as_view(),
        name="preference_list",
    ),
    path(
        "preferences/<str:pk>/",
        PreferenceDetailView.as_view(),
        name="preference_detail",
    ),
    path(
        "preferences/<str:pk>/crawl-now/",
        PreferenceCrawlNowView.as_view(),
        name="preference_crawl_now",
    ),
    path("plans/", PlanListView.as_view(), name="plan_list"),
    path("plans/new/", PlanCreateView.as_view(), name="plan_create"),
    path("plans/<str:pk>/edit/", PlanUpdateView.as_view(), name="plan_update"),
    path("plans/<str:pk>/delete/", PlanDeleteView.as_view(), name="plan_delete"),
    path("subscriptions/", SubscriptionListView.as_view(), name="subscription_list"),
    path(
        "subscriptions/<str:pk>/",
        SubscriptionDetailView.as_view(),
        name="subscription_detail",
    ),
    path("settings/smtp-test/", SmtpTestView.as_view(), name="smtp_test"),
    path("assessments/", include("assessment.urls")),
    path("profiles/", include("profiles.urls")),
    path("jobs/", include("jobs.urls")),
    path("api/v1/", include("api.v1.urls")),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
]
