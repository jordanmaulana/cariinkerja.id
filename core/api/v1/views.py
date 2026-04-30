from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from core.api.v1.serializers import (
    AssessmentSerializer,
    AssessmentStatusUpdateSerializer,
    LoginSerializer,
    OnboardingSerializer,
    ProfileSerializer,
    SignupSerializer,
    UserSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token = serializer.context["token"]
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_me(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(ProfileSerializer(profile).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def onboarding(request):
    serializer = OnboardingSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    profile = serializer.save()
    return Response(ProfileSerializer(profile).data)


def _user_assessments(user):
    return Assessment.objects.filter(preference__profile__user=user).select_related(
        "job", "preference"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_list(request):
    qs = _user_assessments(request.user).order_by("-created_on")
    status_param = request.query_params.get("status")
    if status_param:
        if status_param not in AssessmentStatus.values:
            return Response(
                {"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )
        qs = qs.filter(status=status_param)
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
    return Response(AssessmentSerializer(qs, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def assessment_detail(request, pk):
    assessment = get_object_or_404(_user_assessments(request.user), pk=pk)
    if request.method == "GET":
        return Response(AssessmentSerializer(assessment).data)
    serializer = AssessmentStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        assessment.status = serializer.validated_data["status"]
        assessment.save(update_fields=["status", "updated_on"])
    return Response(AssessmentSerializer(assessment).data)
