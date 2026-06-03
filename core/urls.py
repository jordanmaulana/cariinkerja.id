"""URL configuration for core project."""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import (
    AdminLoginView,
    DashboardChartsFragmentView,
    DashboardRecentAssessmentsFragmentView,
    DashboardTopProfilesFragmentView,
    DashboardView,
    PlanCreateView,
    PlanDeleteView,
    PlanListView,
    PlanUpdateView,
    PreferenceCrawlNowView,
    PreferenceDetailView,
    PreferenceListView,
    PreferenceRegenerateAllUrlsView,
    PreferenceRegenerateUrlsView,
    SmtpTestView,
    SubscriptionDetailView,
    SubscriptionListView,
)
from jobs.views import (
    CrawlHealthCreateView,
    CrawlHealthDeleteView,
    CrawlHealthListView,
    CrawlHealthRunView,
    CrawlHealthUpdateView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", AdminLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "dashboard/fragments/charts/",
        DashboardChartsFragmentView.as_view(),
        name="dashboard_fragment_charts",
    ),
    path(
        "dashboard/fragments/top-profiles/",
        DashboardTopProfilesFragmentView.as_view(),
        name="dashboard_fragment_top_profiles",
    ),
    path(
        "dashboard/fragments/recent-assessments/",
        DashboardRecentAssessmentsFragmentView.as_view(),
        name="dashboard_fragment_recent_assessments",
    ),
    path(
        "preferences/",
        PreferenceListView.as_view(),
        name="preference_list",
    ),
    path(
        "preferences/regenerate-all-urls/",
        PreferenceRegenerateAllUrlsView.as_view(),
        name="preference_regenerate_all_urls",
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
    path(
        "preferences/<str:pk>/regenerate-urls/",
        PreferenceRegenerateUrlsView.as_view(),
        name="preference_regenerate_urls",
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
    path("crawl-health/", CrawlHealthListView.as_view(), name="crawl_health_list"),
    path(
        "crawl-health/new/",
        CrawlHealthCreateView.as_view(),
        name="crawl_health_create",
    ),
    path(
        "crawl-health/run/",
        CrawlHealthRunView.as_view(),
        name="crawl_health_run",
    ),
    path(
        "crawl-health/<str:pk>/edit/",
        CrawlHealthUpdateView.as_view(),
        name="crawl_health_update",
    ),
    path(
        "crawl-health/<str:pk>/delete/",
        CrawlHealthDeleteView.as_view(),
        name="crawl_health_delete",
    ),
    path("settings/smtp-test/", SmtpTestView.as_view(), name="smtp_test"),
    path("assessments/", include("assessment.urls")),
    path("profiles/", include("profiles.urls")),
    path("jobs/", include("jobs.urls")),
    path("api/v1/", include("api.v1.urls")),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
]
