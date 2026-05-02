from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from core.models import Plan, Subscription, effective_price
from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from profiles.models import Preference, Profile

User = get_user_model()


class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField()

    def validate(self, attrs):
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        if not client_id:
            raise serializers.ValidationError("Google sign-in is not configured.")
        try:
            claims = id_token.verify_oauth2_token(
                attrs["credential"], google_requests.Request(), client_id
            )
        except ValueError:
            raise serializers.ValidationError("Invalid Google credential.")
        if not claims.get("email"):
            raise serializers.ValidationError("Google account has no email.")
        if not claims.get("email_verified"):
            raise serializers.ValidationError("Google email is not verified.")
        attrs["claims"] = claims
        return attrs


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    onboarded = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "onboarded"]

    def _profile(self, user):
        return getattr(user, "profile", None)

    def get_full_name(self, user):
        profile = self._profile(user)
        return profile.full_name if profile else None

    def get_onboarded(self, user):
        profile = self._profile(user)
        return bool(profile and profile.full_name)


class ProfileSerializer(serializers.ModelSerializer):
    onboarded = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "suggested_full_name",
            "linkedin_url",
            "bio",
            "onboarded",
            "open_to_work",
        ]
        read_only_fields = ["open_to_work"]

    def get_onboarded(self, profile):
        return bool(profile.full_name)


class OnboardingSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    job_type = serializers.ChoiceField(choices=JobType.choices)
    remote_option = serializers.ChoiceField(choices=RemoteOption.choices)

    def save(self, **kwargs):
        user = self.context["request"].user
        data = self.validated_data
        with transaction.atomic():
            profile = user.profile
            profile.full_name = data["full_name"]
            profile.linkedin_url = data.get("linkedin_url") or None
            profile.bio = data.get("bio") or None
            profile.save()
            Preference.objects.create(
                profile=profile,
                title=data["title"],
                job_type=data["job_type"],
                remote_option=data["remote_option"],
            )
        return profile


class JobBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company",
            "location",
            "url",
            "job_type",
            "remote_option",
        ]


class PreferenceBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = ["id", "title"]


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = [
            "id",
            "title",
            "job_type",
            "remote_option",
            "crawl_url",
            "crawl_source",
            "status",
            "created_on",
            "updated_on",
        ]
        read_only_fields = ["id", "crawl_url", "status", "created_on", "updated_on"]


class AssessmentSerializer(serializers.ModelSerializer):
    job = JobBriefSerializer(read_only=True)
    preference = PreferenceBriefSerializer(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "status",
            "score",
            "verdict",
            "created_on",
            "job",
            "preference",
            "soft_skill_match",
            "soft_skill_gap",
            "hard_skill_match",
            "hard_skill_gap",
        ]


class AssessmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AssessmentStatus.choices)


class PlanSerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = ["id", "name", "price", "effective_price", "preference_limit"]

    def get_effective_price(self, plan):
        request = self.context.get("request")
        profile = None
        if request is not None and request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
        return effective_price(
            plan, profile, cheapest_id=self.context.get("cheapest_plan_id")
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "started_at",
            "expires_at",
            "payment_link",
            "created_on",
        ]


class CheckoutSerializer(serializers.Serializer):
    plan_id = serializers.CharField()
