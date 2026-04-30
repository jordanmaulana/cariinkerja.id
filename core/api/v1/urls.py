from django.urls import path

from core.api.v1.views import (
    assessment_detail,
    assessment_list,
    dashboard_stats,
    login,
    logout,
    me,
    onboarding,
    preference_detail,
    preference_list,
    profile_me,
    signup,
)

urlpatterns = [
    path("auth/signup/", signup, name="api-v1-signup"),
    path("auth/login/", login, name="api-v1-login"),
    path("auth/logout/", logout, name="api-v1-logout"),
    path("auth/me/", me, name="api-v1-me"),
    path("profile/me/", profile_me, name="api-v1-profile-me"),
    path("onboarding/", onboarding, name="api-v1-onboarding"),
    path("dashboard/stats/", dashboard_stats, name="api-v1-dashboard-stats"),
    path("preferences/", preference_list, name="api-v1-preference-list"),
    path("preferences/<str:pk>/", preference_detail, name="api-v1-preference-detail"),
    path("assessments/", assessment_list, name="api-v1-assessment-list"),
    path("assessments/<str:pk>/", assessment_detail, name="api-v1-assessment-detail"),
]
