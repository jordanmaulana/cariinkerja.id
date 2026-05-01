"""URL configuration for core project."""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import (
    AdminLoginView,
    DashboardView,
    PreferenceCrawlNowView,
    PreferenceDetailView,
    PreferenceListView,
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
    path("assessments/", include("assessment.urls")),
    path("profiles/", include("profiles.urls")),
    path("jobs/", include("jobs.urls")),
    path("api/", include("core.api.urls")),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
]
