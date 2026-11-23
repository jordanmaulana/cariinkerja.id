from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from billing.models import Plan, Subscription, effective_price
from core.jev import INVALID, MULTIPLE, classify_job_title
from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from profiles.models import Preference, Profile
from profiles.services import (
    RESUME_MAX_BYTES,
    RESUME_MAX_TEXT_CHARS,
    RESUME_MIN_CHARS,
    extract_pdf_text,
)

User = get_user_model()

JOB_TITLE_ERRORS = {
    INVALID: "Tolong masukin job title yang valid dong",
    MULTIPLE: (
        "Pilih 1 job title aja yang paling dikuasai. Pencarian lebih dari 1 job "
        "title tersedia di fitur pro. Tambahkan di halaman Pencarian"
    ),
}


def _validate_job_title(value):
    error = JOB_TITLE_ERRORS.get(classify_job_title(value))
    if error:
        raise serializers.ValidationError(error)
    return value


def _resume_text(f):
    """A CV PDF's extracted text; the PDF itself is never stored."""
    if f.size > RESUME_MAX_BYTES:
        raise serializers.ValidationError("CV maksimal 5 MB.")
    try:
        text = extract_pdf_text(f)
    except ValueError:
        raise serializers.ValidationError(
            "PDF-nya nggak kebaca. Coba export ulang CV-mu ke PDF."
        )
    if len(text.strip()) < RESUME_MIN_CHARS:
        raise serializers.ValidationError(
            "Teks di CV-mu nggak kebaca (kayaknya hasil scan). Upload PDF "
            "yang teksnya bisa di-copy, atau pakai LinkedIn."
        )
    return text


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
    cv_text = serializers.SerializerMethodField()
    cv_next_edit_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "suggested_full_name",
            "phone",
            "linkedin_url",
            "bio",
            "onboarded",
            "open_to_work",
            "whitelist",
            "linkedin_quality_ok",
            "linkedin_quality_reason",
            "linkedin_ingested_at",
            "cv_text",
            "cv_next_edit_at",
        ]
        read_only_fields = [
            "open_to_work",
            "whitelist",
            "linkedin_quality_ok",
            "linkedin_quality_reason",
            "linkedin_ingested_at",
        ]

    def get_onboarded(self, profile):
        return bool(profile.full_name)

    def get_cv_text(self, profile):
        # CV profiles only: a LinkedIn profile's raw is an Apify dump, not theirs to edit.
        return None if profile.linkedin_url else profile.linkedin_raw


class ProfileCvSerializer(serializers.Serializer):
    """Replace a CV profile's text: edited text, or a fresh PDF. Exactly one."""

    cv_text = serializers.CharField(
        required=False,
        min_length=RESUME_MIN_CHARS,
        max_length=RESUME_MAX_TEXT_CHARS,
        error_messages={
            "blank": "Teks CV nggak boleh kosong.",
            "min_length": "Teks CV kependekan buat dinilai.",
            "max_length": "Teks CV kepanjangan, ringkas dulu ya.",
        },
    )
    resume = serializers.FileField(required=False)

    def validate_resume(self, f):
        return _resume_text(f)

    def validate(self, attrs):
        if bool(attrs.get("cv_text")) == bool(attrs.get("resume")):
            raise serializers.ValidationError(
                "Kirim teks CV atau file PDF, pilih salah satu."
            )
        return attrs

    def save(self, **kwargs):
        from profiles.tasks import crawl_linkedin_for_profile

        profile = self.context["profile"]
        text = self.validated_data.get("resume") or self.validated_data["cv_text"]
        # Unchanged text = no LLM call, and it doesn't use up today's edit.
        if text.strip() != (profile.linkedin_raw or "").strip():
            with transaction.atomic():
                profile.linkedin_raw = text
                profile.cv_updated_at = timezone.now()
                profile.save(
                    update_fields=["linkedin_raw", "cv_updated_at", "updated_on"]
                )
                transaction.on_commit(
                    lambda: crawl_linkedin_for_profile.delay(profile.id)
                )
        return profile


class OnboardingSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32)
    # Exactly one of linkedin_url / resume (a CV PDF), see validate().
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    resume = serializers.FileField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    job_type = serializers.ListField(
        child=serializers.ChoiceField(choices=JobType.choices),
        allow_empty=True,
        required=False,
        default=list,
    )
    remote_option = serializers.ListField(
        child=serializers.ChoiceField(choices=RemoteOption.choices),
        allow_empty=True,
        required=False,
        default=list,
    )

    def validate_title(self, value):
        return _validate_job_title(value)

    def validate_resume(self, f):
        return _resume_text(f)

    def validate(self, attrs):
        if bool(attrs.get("linkedin_url")) == bool(attrs.get("resume")):
            raise serializers.ValidationError(
                "Isi URL LinkedIn atau upload CV, pilih salah satu."
            )
        return attrs

    def save(self, **kwargs):
        from profiles.services import prepare_preference_for_payment
        from profiles.tasks import crawl_linkedin_for_profile

        user = self.context["request"].user
        data = self.validated_data
        with transaction.atomic():
            profile = user.profile
            profile.full_name = data["full_name"]
            profile.phone = data["phone"]
            profile.linkedin_url = data.get("linkedin_url") or None
            if data.get("resume"):
                profile.linkedin_raw = data["resume"]
            profile.bio = data.get("bio") or None
            profile.save()
            preference = Preference.objects.create(
                profile=profile,
                title=data["title"],
                job_type=data["job_type"],
                remote_option=data["remote_option"],
            )
            # Free crawl disabled: make the preference payable immediately
            # (fills crawl_urls + flips to WAITING_PAYMENT) instead of waiting
            # in WAITING_ADMIN for LinkedIn ingest. Ingest still runs on_commit
            # below for assessment quality + Open-to-Work discount.
            prepare_preference_for_payment(preference, require_full_profile=False)
            transaction.on_commit(
                lambda: crawl_linkedin_for_profile.delay(profile.id, preference.id)
            )
        return profile


class JobTitleCheckSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)

    def validate_title(self, value):
        return _validate_job_title(value)


class JobBriefSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()

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
            "is_expired",
            "source",
        ]

    def get_is_expired(self, obj) -> bool:
        return bool(obj.expires_at and obj.expires_at <= timezone.now())


class PreferenceBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = ["id", "title"]


class PreferenceSerializer(serializers.ModelSerializer):
    job_type = serializers.ListField(
        child=serializers.ChoiceField(choices=JobType.choices),
        allow_empty=True,
        required=False,
        default=list,
    )
    remote_option = serializers.ListField(
        child=serializers.ChoiceField(choices=RemoteOption.choices),
        allow_empty=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Preference
        fields = [
            "id",
            "title",
            "job_type",
            "remote_option",
            "crawl_urls",
            "status",
            "created_on",
            "updated_on",
        ]
        read_only_fields = [
            "id",
            "crawl_urls",
            "status",
            "created_on",
            "updated_on",
        ]

    def validate_title(self, value):
        # Unchanged title on edit skips the (paid, networked) check.
        if not value or (self.instance and value == self.instance.title):
            return value
        return _validate_job_title(value)


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
        fields = [
            "id",
            "name",
            "price",
            "effective_price",
            "preference_limit",
            "duration_days",
        ]

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
