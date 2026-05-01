from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from profiles.consts import Status
from profiles.models import Preference, Profile
from profiles.services import LinkedInIngest, ingest_linkedin

_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _mock_openai(parsed: LinkedInIngest):
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(parsed=parsed))]
    client.chat.completions.parse.return_value = response
    return client


class IngestLinkedInTests(TestCase):
    @patch("profiles.services.OpenAI")
    def test_ingest_clean_profile(self, openai_cls):
        parsed = LinkedInIngest(
            cleaned_full_profile="About: senior backend engineer...",
            is_sparse=False,
            sparse_reason="",
            open_to_work=False,
            quality_notes="Solid Go and Django background.",
        )
        openai_cls.return_value = _mock_openai(parsed)

        result = ingest_linkedin("raw blob")

        self.assertEqual(result.cleaned_full_profile, parsed.cleaned_full_profile)
        self.assertFalse(result.is_sparse)
        self.assertFalse(result.open_to_work)

    @patch("profiles.services.OpenAI")
    def test_ingest_sparse_profile(self, openai_cls):
        parsed = LinkedInIngest(
            cleaned_full_profile="Engineer at Foo. Engineer at Bar.",
            is_sparse=True,
            sparse_reason="3 roles listed but zero have descriptions; no About section",
            open_to_work=False,
            quality_notes="Insufficient detail.",
        )
        openai_cls.return_value = _mock_openai(parsed)

        result = ingest_linkedin("raw blob")

        self.assertTrue(result.is_sparse)
        self.assertIn("descriptions", result.sparse_reason)

    @patch("profiles.services.OpenAI")
    def test_ingest_open_to_work(self, openai_cls):
        parsed = LinkedInIngest(
            cleaned_full_profile="...",
            is_sparse=False,
            sparse_reason="",
            open_to_work=True,
            quality_notes="OK",
        )
        openai_cls.return_value = _mock_openai(parsed)

        result = ingest_linkedin("Header includes #OPEN_TO_WORK")

        self.assertTrue(result.open_to_work)


@override_settings(STORAGES=_TEST_STORAGES)
class ProfileDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            "owner", "owner@example.com", "secret"
        )
        self.client.force_login(self.user)
        self.profile = Profile.objects.create(full_name="Jane")

    @patch("profiles.views.ingest_linkedin")
    def test_profile_detail_post_runs_ingest(self, ingest):
        ingest.return_value = LinkedInIngest(
            cleaned_full_profile="Cleaned content",
            is_sparse=False,
            sparse_reason="",
            open_to_work=True,
            quality_notes="Strong profile",
        )

        url = reverse("profile_detail", args=[self.profile.id])
        resp = self.client.post(
            url,
            {
                "full_name": "Jane Doe",
                "linkedin_url": "https://linkedin.com/in/jane",
                "bio": "",
                "linkedin_raw": "raw paste from linkedin",
                "full_profile": "",
            },
        )

        self.assertEqual(resp.status_code, 302)
        ingest.assert_called_once_with("raw paste from linkedin")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.linkedin_raw, "raw paste from linkedin")
        self.assertEqual(self.profile.full_profile, "Cleaned content")
        self.assertTrue(self.profile.open_to_work)
        self.assertTrue(self.profile.linkedin_quality_ok)
        self.assertEqual(self.profile.linkedin_quality_reason, "Strong profile")
        self.assertIsNotNone(self.profile.linkedin_ingested_at)

    @patch("profiles.views.ingest_linkedin")
    def test_manual_open_to_work_toggle(self, ingest):
        url = reverse("profile_detail", args=[self.profile.id])
        resp = self.client.post(
            url,
            {
                "full_name": "Jane",
                "linkedin_url": "",
                "bio": "",
                "linkedin_raw": "",
                "full_profile": "",
                "open_to_work": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        ingest.assert_not_called()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.open_to_work)

    @patch("profiles.views.ingest_linkedin")
    def test_override_skips_ingest(self, ingest):
        url = reverse("profile_detail", args=[self.profile.id])
        resp = self.client.post(
            url,
            {
                "full_name": "Jane",
                "linkedin_url": "",
                "bio": "",
                "linkedin_raw": "",
                "full_profile": "manual content",
                "manual_full_profile_override": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        ingest.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_profile, "manual content")


@override_settings(STORAGES=_TEST_STORAGES)
class PreferenceQualityGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            "owner", "owner@example.com", "secret"
        )
        self.client.force_login(self.user)
        self.profile = Profile.objects.create(
            full_name="Sparse Sally",
            linkedin_quality_ok=False,
            linkedin_quality_reason="titles only",
        )
        self.pref = Preference.objects.create(
            profile=self.profile, status=Status.WAITING_PAYMENT
        )

    def test_advance_blocked_when_sparse(self):
        url = reverse("preference_detail", args=[self.pref.id])
        resp = self.client.post(
            url,
            {
                "crawl_url": "",
                "crawl_source": "",
                "status": Status.RUNNING,
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.pref.refresh_from_db()
        self.assertEqual(self.pref.status, Status.WAITING_PAYMENT)

    def test_advance_allowed_with_override(self):
        url = reverse("preference_detail", args=[self.pref.id])
        resp = self.client.post(
            url,
            {
                "crawl_url": "",
                "crawl_source": "",
                "status": Status.RUNNING,
                "override_quality_gate": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.pref.refresh_from_db()
        self.assertEqual(self.pref.status, Status.RUNNING)
