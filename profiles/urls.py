from django.urls import path

from profiles.views import (
    ProfileDetailView,
    ProfileListView,
    ProfileReingestLinkedinView,
)

urlpatterns = [
    path("", ProfileListView.as_view(), name="profile_list"),
    path(
        "<str:pk>/reingest-linkedin/",
        ProfileReingestLinkedinView.as_view(),
        name="profile_reingest_linkedin",
    ),
    path("<str:pk>/", ProfileDetailView.as_view(), name="profile_detail"),
]
