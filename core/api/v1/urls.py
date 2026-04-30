from django.urls import path

from core.api.v1.views import login, logout, me, onboarding, profile_me, signup

urlpatterns = [
    path("auth/signup/", signup, name="api-v1-signup"),
    path("auth/login/", login, name="api-v1-login"),
    path("auth/logout/", logout, name="api-v1-logout"),
    path("auth/me/", me, name="api-v1-me"),
    path("profile/me/", profile_me, name="api-v1-profile-me"),
    path("onboarding/", onboarding, name="api-v1-onboarding"),
]
