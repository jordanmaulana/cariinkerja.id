from django.urls import path

from assessment.views import (
    AssessmentDetailView,
    AssessmentListView,
    AssessmentReassessView,
)

urlpatterns = [
    path("", AssessmentListView.as_view(), name="assessment_list"),
    path("<str:pk>/", AssessmentDetailView.as_view(), name="assessment_detail"),
    path(
        "<str:pk>/reassess/",
        AssessmentReassessView.as_view(),
        name="assessment_reassess",
    ),
]
