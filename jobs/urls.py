from django.urls import path

from jobs.views import JobDetailView, JobListView

urlpatterns = [
    path("", JobListView.as_view(), name="job_list"),
    path("<str:pk>/", JobDetailView.as_view(), name="job_detail"),
]
