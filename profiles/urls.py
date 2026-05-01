from django.urls import path

from profiles.views import ProfileDetailView, ProfileListView

urlpatterns = [
    path("", ProfileListView.as_view(), name="profile_list"),
    path("<str:pk>/", ProfileDetailView.as_view(), name="profile_detail"),
]
