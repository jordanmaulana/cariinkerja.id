from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from jobs.consts import JobType, RemoteOption
from jobs.url_builders import build_crawl_urls
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

    @patch("profiles.views.ingest_linkedin")
    def test_resubmitting_identical_raw_skips_ingest(self, ingest):
        # The Save gate only runs the LLM on *changed* raw. Documented here
        # because it is the reason ProfileRegenerateFullProfileView exists.
        self.profile.linkedin_raw = "unchanged raw"
        self.profile.save()

        url = reverse("profile_detail", args=[self.profile.id])
        resp = self.client.post(
            url,
            {
                "full_name": "Jane",
                "linkedin_url": "",
                "bio": "",
                "linkedin_raw": "unchanged raw",
                "full_profile": "",
            },
        )

        self.assertEqual(resp.status_code, 302)
        ingest.assert_not_called()


@override_settings(STORAGES=_TEST_STORAGES)
class ProfileRegenerateFullProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            "owner", "owner@example.com", "secret"
        )
        self.client.force_login(self.user)
        self.profile = Profile.objects.create(
            full_name="Jane",
            linkedin_raw="stored raw",
            full_profile="stale content",
        )
        self.url = reverse("profile_regenerate_full_profile", args=[self.profile.id])

    @patch("profiles.views.ingest_linkedin")
    def test_regenerate_reruns_llm_on_stored_raw(self, ingest):
        ingest.return_value = LinkedInIngest(
            cleaned_full_profile="Cleaned content",
            is_sparse=False,
            sparse_reason="",
            open_to_work=True,
            quality_notes="Strong profile",
        )

        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 302)
        ingest.assert_called_once_with("stored raw")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_profile, "Cleaned content")
        # The source paste must survive a regenerate untouched.
        self.assertEqual(self.profile.linkedin_raw, "stored raw")
        self.assertTrue(self.profile.open_to_work)
        self.assertTrue(self.profile.linkedin_quality_ok)
        self.assertEqual(self.profile.linkedin_quality_reason, "Strong profile")
        self.assertIsNotNone(self.profile.linkedin_ingested_at)

    @patch("profiles.views.ingest_linkedin")
    def test_regenerate_marks_sparse_profile(self, ingest):
        ingest.return_value = LinkedInIngest(
            cleaned_full_profile="Engineer at Foo.",
            is_sparse=True,
            sparse_reason="no descriptions",
            open_to_work=False,
            quality_notes="thin",
        )

        self.client.post(self.url)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.linkedin_quality_ok)
        self.assertEqual(self.profile.linkedin_quality_reason, "no descriptions")

    @patch("profiles.views.ingest_linkedin")
    def test_regenerate_without_raw_is_noop(self, ingest):
        bare = Profile.objects.create(full_name="No Raw")
        url = reverse("profile_regenerate_full_profile", args=[bare.id])

        resp = self.client.post(url)

        self.assertEqual(resp.status_code, 302)
        ingest.assert_not_called()

    @patch("profiles.views.ingest_linkedin")
    def test_regenerate_llm_failure_preserves_existing(self, ingest):
        ingest.side_effect = Exception("boom")

        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_profile, "stale content")
        self.assertIsNone(self.profile.linkedin_ingested_at)

    @patch("profiles.views.ingest_linkedin")
    def test_regenerate_requires_superuser(self, ingest):
        # SuperuserRequiredMixin bounces non-superusers to the login page.
        self.client.force_login(
            User.objects.create_user("plain", "plain@example.com", "secret")
        )
        resp = self.client.post(self.url)

        self.assertIn("/login/", resp.url)
        ingest.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_profile, "stale content")


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
                "crawl_urls": "",
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
                "crawl_urls": "",
                "status": Status.RUNNING,
                "override_quality_gate": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.pref.refresh_from_db()
        self.assertEqual(self.pref.status, Status.RUNNING)


class PrepareForPaymentTests(TestCase):
    """The post_save signal on Preference invokes prepare_preference_for_payment,
    so we observe its effect via .objects.create() rather than calling it again
    (the second call returns False due to the idempotency check on crawl_urls).
    The free crawl on registration is disabled: the preference is advanced to
    WAITING_PAYMENT with crawl_urls filled, but NO crawl is queued.
    """

    def setUp(self):
        self.profile = Profile.objects.create(
            full_name="Cody Coder",
            full_profile="Plenty of substantive content here.",
        )

    @patch("assessment.tasks.crawl_and_assess_preference")
    def test_appends_indeed_and_jobstreet_urls(self, crawl_and_assess_preference):
        pref = Preference.objects.create(
            profile=self.profile,
            title="Mobile Developer",
            job_type=[JobType.FULL_TIME],
            remote_option=[RemoteOption.ON_SITE],
            status=Status.WAITING_ADMIN,
        )
        pref.refresh_from_db()

        self.assertEqual(len(pref.crawl_urls), 3)
        self.assertIn("id.indeed.com/jobs?q=Mobile+Developer", pref.crawl_urls[0])
        self.assertEqual(
            pref.crawl_urls[1],
            "https://id.jobstreet.com/mobile-developer-jobs/full-time/on-site",
        )
        self.assertIn("www.linkedin.com/jobs/search/", pref.crawl_urls[2])
        self.assertIn("keywords=Mobile+Developer", pref.crawl_urls[2])
        # Free crawl disabled: pref advances to WAITING_PAYMENT, no crawl queued.
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)
        crawl_and_assess_preference.delay.assert_not_called()

    def test_remote_preference_appends_emea_linkedin(self):
        pref = Preference.objects.create(
            profile=self.profile,
            title="Mobile Developer",
            remote_option=[RemoteOption.REMOTE],
            status=Status.WAITING_ADMIN,
        )
        pref.refresh_from_db()

        self.assertEqual(len(pref.crawl_urls), 4)
        self.assertIn("www.linkedin.com/jobs/search/", pref.crawl_urls[3])
        self.assertIn("geoId=91000007", pref.crawl_urls[3])
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)

    def test_no_filters_yields_base_jobstreet_url(self):
        pref = Preference.objects.create(
            profile=self.profile,
            title="Developer",
            status=Status.WAITING_ADMIN,
        )
        pref.refresh_from_db()

        self.assertEqual(len(pref.crawl_urls), 3)
        self.assertEqual(pref.crawl_urls[1], "https://id.jobstreet.com/developer-jobs")
        self.assertIn("www.linkedin.com/jobs/search/", pref.crawl_urls[2])
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)

    def test_require_full_profile_false_advances_without_full_profile(self):
        # Registration path: pref becomes payable immediately even before
        # LinkedIn ingest sets full_profile.
        from profiles.services import prepare_preference_for_payment

        bare = Profile.objects.create(full_name="No LinkedIn Yet")
        pref = Preference.objects.create(
            profile=bare,
            title="Developer",
            status=Status.WAITING_ADMIN,
        )
        # The post_save signal (require_full_profile=True) is a no-op here.
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.WAITING_ADMIN)
        self.assertEqual(pref.crawl_urls, [])

        advanced = prepare_preference_for_payment(pref, require_full_profile=False)
        self.assertTrue(advanced)
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)
        self.assertTrue(pref.crawl_urls)


class PreferenceDetailAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", "user@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="User")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = lambda pk: reverse("api-v1-preference-detail", args=[pk])

    def _pref(self, status=Status.WAITING_PAYMENT, **kwargs):
        return Preference.objects.create(
            profile=self.profile, title="Engineer", status=status, **kwargs
        )

    def test_patch_running_keeps_status_and_regenerates_urls(self):
        pref = self._pref(status=Status.RUNNING)
        resp = self.api.patch(self.url(pref.id), {"title": "New"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], Status.RUNNING)
        self.assertEqual(resp.data["title"], "New")
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.RUNNING)
        self.assertEqual(pref.title, "New")
        self.assertEqual(
            pref.crawl_urls, build_crawl_urls("New", pref.job_type, pref.remote_option)
        )

    def test_patch_waiting_payment_keeps_status(self):
        pref = self._pref(status=Status.WAITING_PAYMENT)
        resp = self.api.patch(self.url(pref.id), {"title": "X"}, format="json")
        self.assertEqual(resp.status_code, 200)
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)
        self.assertEqual(pref.title, "X")

    def test_patch_waiting_admin_keeps_status(self):
        pref = self._pref(status=Status.WAITING_ADMIN)
        resp = self.api.patch(self.url(pref.id), {"title": "X"}, format="json")
        self.assertEqual(resp.status_code, 200)
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.WAITING_ADMIN)

    def test_patch_expired_keeps_status(self):
        pref = self._pref(status=Status.EXPIRED)
        resp = self.api.patch(self.url(pref.id), {"title": "X"}, format="json")
        self.assertEqual(resp.status_code, 200)
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.EXPIRED)

    def test_delete_allowed_when_waiting_payment(self):
        pref = self._pref(status=Status.WAITING_PAYMENT)
        resp = self.api.delete(self.url(pref.id))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Preference.objects.filter(pk=pref.id).exists())

    def test_delete_blocked_when_waiting_admin(self):
        pref = self._pref(status=Status.WAITING_ADMIN)
        resp = self.api.delete(self.url(pref.id))
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Preference.objects.filter(pk=pref.id).exists())

    def test_delete_blocked_when_running(self):
        pref = self._pref(status=Status.RUNNING)
        resp = self.api.delete(self.url(pref.id))
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Preference.objects.filter(pk=pref.id).exists())

    def test_delete_blocked_when_expired(self):
        pref = self._pref(status=Status.EXPIRED)
        resp = self.api.delete(self.url(pref.id))
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Preference.objects.filter(pk=pref.id).exists())

    def test_user_cannot_set_status_directly(self):
        pref = self._pref(status=Status.WAITING_PAYMENT)
        resp = self.api.patch(
            self.url(pref.id), {"status": Status.RUNNING}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        pref.refresh_from_db()
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)

    def test_user_cannot_set_crawl_urls(self):
        pref = self._pref(status=Status.WAITING_PAYMENT, crawl_urls=[])
        resp = self.api.patch(
            self.url(pref.id),
            {"crawl_urls": ["https://evil.example.com/inject"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        pref.refresh_from_db()
        # Injected URL ignored; crawl_urls regenerated from the title.
        self.assertNotIn("https://evil.example.com/inject", pref.crawl_urls)
        self.assertEqual(
            pref.crawl_urls,
            build_crawl_urls("Engineer", pref.job_type, pref.remote_option),
        )


class OnboardingAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", "user@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user)
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = reverse("api-v1-onboarding")
        self.payload = {
            "full_name": "Jane Doe",
            "phone": "08123456789",
            "linkedin_url": "https://www.linkedin.com/in/jane-doe",
            "title": "Backend Engineer",
            "job_type": [JobType.FULL_TIME],
            "remote_option": [RemoteOption.REMOTE],
        }

    def test_onboarding_persists_phone_and_creates_preference(self):
        resp = self.api.post(self.url, self.payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["phone"], "08123456789")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone, "08123456789")
        self.assertEqual(self.profile.full_name, "Jane Doe")
        pref = Preference.objects.get(profile=self.profile)
        # Registration makes the preference payable immediately: crawl_urls
        # filled + status WAITING_PAYMENT (no crawl runs). LinkedIn ingests
        # in the background.
        self.assertEqual(pref.status, Status.WAITING_PAYMENT)
        self.assertTrue(pref.crawl_urls)
        self.assertEqual(pref.title, "Backend Engineer")

    def test_onboarding_missing_phone_rejected(self):
        payload = dict(self.payload)
        del payload["phone"]
        resp = self.api.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("phone", resp.data)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.phone)
        self.assertFalse(Preference.objects.filter(profile=self.profile).exists())

    def test_onboarding_blank_phone_rejected(self):
        payload = dict(self.payload, phone="")
        resp = self.api.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("phone", resp.data)
        self.assertFalse(Preference.objects.filter(profile=self.profile).exists())
