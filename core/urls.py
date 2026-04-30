"""URL configuration for core project."""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from core.views import AdminLoginView, DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", AdminLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
]
