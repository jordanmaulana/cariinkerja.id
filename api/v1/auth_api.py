from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import GoogleAuthSerializer, UserSerializer
from profiles.models import Profile

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def google(request):
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    claims = serializer.validated_data["claims"]
    email = claims["email"].lower()
    google_name = (claims.get("name") or "").strip()
    with transaction.atomic():
        user = User.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            user = User.objects.create_user(username=email, email=email)
            created = True
        profile, _ = Profile.objects.get_or_create(user=user)
        if (
            google_name
            and not profile.full_name
            and profile.suggested_full_name != google_name
        ):
            profile.suggested_full_name = google_name
            profile.save()
        token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
