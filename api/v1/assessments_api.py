from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import AssessmentSerializer, AssessmentStatusUpdateSerializer
from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from core.realtime import publish, user_channel


def _user_assessments(user):
    return Assessment.objects.filter(
        preference__profile__user=user, is_relevant=True
    ).select_related("job", "preference")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list(request):
    qs = _user_assessments(request.user).order_by("-created_on")
    status_values = request.query_params.getlist("status")
    if status_values:
        for value in status_values:
            if value not in AssessmentStatus.values:
                return Response(
                    {"detail": "Invalid status."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        qs = qs.filter(status__in=status_values)
    min_score_param = request.query_params.get("min_score")
    if min_score_param:
        try:
            min_score = int(min_score_param)
        except ValueError:
            return Response(
                {"detail": "Invalid min_score."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = qs.filter(score__gte=min_score)

    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        return Response({"detail": "Invalid page."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        page_size = int(request.query_params.get("page_size", 25))
    except ValueError:
        return Response(
            {"detail": "Invalid page_size."}, status=status.HTTP_400_BAD_REQUEST
        )
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
        results = AssessmentSerializer(page_obj.object_list, many=True).data
    except EmptyPage:
        results = []

    return Response(
        {
            "count": paginator.count,
            "page": page,
            "page_size": page_size,
            "num_pages": paginator.num_pages,
            "results": results,
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def detail(request, pk):
    assessment = get_object_or_404(_user_assessments(request.user), pk=pk)
    if request.method == "GET":
        return Response(AssessmentSerializer(assessment).data)
    serializer = AssessmentStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        assessment.status = serializer.validated_data["status"]
        assessment.save(update_fields=["status", "updated_on"])
    publish(
        user_channel(request.user.id),
        {
            "event": "assessment.status_changed",
            "assessment_id": assessment.id,
            "status": assessment.status,
        },
    )
    return Response(AssessmentSerializer(assessment).data)
