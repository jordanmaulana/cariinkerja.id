from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from assessment.tasks import (
    crawl_and_assess_preference,
    crawl_running_preferences,
    email_morning_high_score_summary,
)
from jobs.models import Job
from profiles.consts import Status as PrefStatus
from profiles.models import Preference, Profile

User = get_user_model()


def _make_job(slug: str, title: str = "Senior Dev") -> Job:
    return Job.objects.create(
        url=f"https://job.test/{slug}",
        title=title,
        description="x",
        location="Jakarta",
        source="jobstreet",
    )


class AssessmentListApiTests(TestCase):
    def test_q_filters_by_job_title(self):
        user = User.objects.create_user(username="u1", email="u1@example.com")
        pref = Preference.objects.create(profile=Profile.objects.create(user=user))
        for slug, title in [("a", "Python Developer"), ("b", "Sales Manager")]:
            Assessment.objects.create(
                job=_make_job(slug, title), preference=pref, score=80, is_relevant=True
            )
        client = APIClient()
        client.force_authenticate(user)

        res = client.get(reverse("api-v1-assessment-list"), {"q": " python "})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["job"]["title"], "Python Developer")

    def test_preference_filters_by_preference(self):
        user = User.objects.create_user(username="u1", email="u1@example.com")
        profile = Profile.objects.create(user=user)
        pref_a = Preference.objects.create(profile=profile, title="Backend")
        pref_b = Preference.objects.create(profile=profile, title="Data")
        Assessment.objects.create(
            job=_make_job("a"), preference=pref_a, score=80, is_relevant=True
        )
        kept = Assessment.objects.create(
            job=_make_job("b"), preference=pref_b, score=80, is_relevant=True
        )
        client = APIClient()
        client.force_authenticate(user)

        res = client.get(reverse("api-v1-assessment-list"), {"preference": pref_b.id})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], kept.id)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="smtp.test",
    EMAIL_HOST_USER="test@cariinkerja.id",
    FRONTEND_URL="https://app.test",
)
class MorningEmailTaskTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="x"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.pref = Preference.objects.create(
            profile=self.profile,
            status=PrefStatus.RUNNING,
            crawl_urls=["https://x"],
        )

    def _make_assessment(
        self,
        *,
        slug: str,
        score: int = 85,
        status: str = AssessmentStatus.NEW,
        is_relevant: bool = True,
        hours_ago: int | None = None,
    ) -> Assessment:
        job = _make_job(slug)
        a = Assessment.objects.create(
            job=job,
            preference=self.pref,
            status=status,
            score=score,
            is_relevant=is_relevant,
        )
        if hours_ago is not None:
            Assessment.objects.filter(pk=a.pk).update(
                created_on=timezone.now() - timedelta(hours=hours_ago)
            )
        return a

    def test_sends_email_with_count_and_link(self):
        self._make_assessment(slug="a", score=90)
        self._make_assessment(slug="b", score=85)
        sent = email_morning_high_score_summary()
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("u1@example.com", msg.to)
        self.assertIn("2 loker", msg.subject)
        self.assertIn("https://app.test/assessments/?status=new&min_score=80", msg.body)

    def test_skips_low_score(self):
        self._make_assessment(slug="a", score=70)
        self.assertEqual(email_morning_high_score_summary(), 0)
        self.assertEqual(mail.outbox, [])

    def test_skips_yesterday(self):
        self._make_assessment(slug="a", score=95, hours_ago=30)
        self.assertEqual(email_morning_high_score_summary(), 0)

    def test_skips_non_new_status(self):
        self._make_assessment(slug="a", score=95, status=AssessmentStatus.SEEN)
        self.assertEqual(email_morning_high_score_summary(), 0)

    def test_skips_irrelevant(self):
        self._make_assessment(slug="a", score=95, is_relevant=False)
        self.assertEqual(email_morning_high_score_summary(), 0)

    def test_skips_profile_without_user(self):
        self.profile.user = None
        self.profile.save()
        self._make_assessment(slug="a", score=95)
        self.assertEqual(email_morning_high_score_summary(), 0)

    def test_skips_user_without_email(self):
        self.user.email = ""
        self.user.save()
        self._make_assessment(slug="a", score=95)
        self.assertEqual(email_morning_high_score_summary(), 0)


class CrawlWhitelistTests(TestCase):
    def test_whitelisted_profile_without_subscription_is_crawled(self):
        u = User.objects.create_user(username="w", email="w@x.com", password="x")
        p = Profile.objects.create(user=u, whitelist=True)
        Preference.objects.create(
            profile=p, status=PrefStatus.RUNNING, crawl_urls=["https://x"]
        )
        with patch("assessment.tasks.crawl_and_assess_preference.delay") as m:
            n = crawl_running_preferences()
        self.assertEqual(n, 1)
        m.assert_called_once()

    def test_non_whitelisted_without_active_sub_is_skipped(self):
        u = User.objects.create_user(username="n", email="n@x.com", password="x")
        p = Profile.objects.create(user=u, whitelist=False)
        Preference.objects.create(
            profile=p, status=PrefStatus.RUNNING, crawl_urls=["https://x"]
        )
        with patch("assessment.tasks.crawl_and_assess_preference.delay") as m:
            n = crawl_running_preferences()
        self.assertEqual(n, 0)
        m.assert_not_called()

    def test_whitelisted_with_empty_crawl_urls_is_skipped(self):
        u = User.objects.create_user(username="e", email="e@x.com", password="x")
        p = Profile.objects.create(user=u, whitelist=True)
        Preference.objects.create(profile=p, status=PrefStatus.RUNNING, crawl_urls=[])
        with patch("assessment.tasks.crawl_and_assess_preference.delay") as m:
            n = crawl_running_preferences()
        self.assertEqual(n, 0)
        m.assert_not_called()


POSTING = {
    "url": "https://job.test/reassess-me",
    "title": "Senior Dev",
    "company": "Acme",
    "description": "fresh description",
    "location": "Jakarta",
    "job_type": None,
    "remote_option": None,
}


class CrawlReassessExistingTests(TestCase):
    def setUp(self):
        u = User.objects.create_user(username="c", email="c@x.com", password="x")
        self.profile = Profile.objects.create(user=u)
        self.pref = Preference.objects.create(
            profile=self.profile,
            title="Senior Dev",
            status=PrefStatus.RUNNING,
            crawl_urls=["https://listing.test/q=dev"],
        )

    def _crawl(self, **kwargs):
        """Run the task against a single fake posting, LLM paths mocked out."""
        scraper = MagicMock()
        scraper.crawl.return_value = [POSTING]
        with (
            patch(
                "assessment.tasks.scraper_for_url", return_value=(scraper, "jobstreet")
            ),
            patch("assessment.tasks.extract_job_skills.delay"),
            patch("assessment.tasks.assess_job.delay") as assess_mock,
            patch("assessment.tasks.reassess_assessment.delay") as reassess_mock,
        ):
            count = crawl_and_assess_preference(self.pref.id, **kwargs)
        return count, assess_mock, reassess_mock

    def _existing_assessment(self) -> Assessment:
        job = Job.objects.create(
            url=POSTING["url"],
            title="Stale title",
            description="stale description",
            location="Jakarta",
            source="jobstreet",
        )
        return Assessment.objects.create(
            job=job, preference=self.pref, score=50, verdict="stale"
        )

    def test_existing_assessment_is_reassessed_when_opted_in(self):
        existing = self._existing_assessment()
        count, assess_mock, reassess_mock = self._crawl(reassess_existing=True)
        self.assertEqual(count, 1)
        reassess_mock.assert_called_once_with(existing.id)
        assess_mock.assert_not_called()

    def test_new_job_is_assessed_normally_when_opted_in(self):
        count, assess_mock, reassess_mock = self._crawl(reassess_existing=True)
        self.assertEqual(count, 1)
        job = Job.objects.get(url=POSTING["url"])
        assess_mock.assert_called_once_with(job.id, self.pref.id)
        reassess_mock.assert_not_called()

    def test_default_does_not_reassess_existing(self):
        """Guards the beat and on-payment paths against re-billing the LLM."""
        self._existing_assessment()
        count, assess_mock, reassess_mock = self._crawl()
        self.assertEqual(count, 1)
        reassess_mock.assert_not_called()
        job = Job.objects.get(url=POSTING["url"])
        assess_mock.assert_called_once_with(job.id, self.pref.id)

    def test_reassess_scores_against_the_refreshed_job(self):
        existing = self._existing_assessment()
        self._crawl(reassess_existing=True)
        existing.job.refresh_from_db()
        self.assertEqual(existing.job.description, POSTING["description"])


class CheckRelevanceTests(TestCase):
    """Guards the gate's inputs and the in-code combination; the model's
    judgement itself is checked live."""

    def setUp(self):
        self.pref = Preference.objects.create(
            profile=Profile.objects.create(full_name="Cody"), title="Engineer"
        )

    def _check(self, remote_option, location="Singapore", **answer):
        from assessment.services import _RelevanceAnswer, check_relevance

        fields = dict(
            same_field=True,
            residency_excludes_indonesia=False,
            requires_foreign_work_authorization=False,
            reason="r",
        )
        fields.update(answer)
        job = Job(
            url="https://x",
            title="Engineer",
            location=location,
            remote_option=remote_option,
            description="x" * 6000 + " Canada residents only.",
        )
        with patch("assessment.services.get_prompt_manager") as get_pm:
            get_pm.return_value.parse.return_value = _RelevanceAnswer(**fields)
            result = check_relevance(job, self.pref)
        return result, get_pm.return_value.parse.call_args.kwargs

    def test_sends_labelled_location_and_description_tail(self):
        from jobs.consts import RemoteOption

        _, kwargs = self._check(RemoteOption.REMOTE, location="United States")
        self.assertIn("APPLICANT LOCATION RESTRICTION: United States", kwargs["user"])
        self.assertIn("JOB REMOTE_OPTION: remote", kwargs["user"])
        self.assertIn("Canada residents only.", kwargs["user"])
        self.assertIn("Indonesia", kwargs["system"])

        _, kwargs = self._check(RemoteOption.ON_SITE)
        self.assertIn("OFFICE LOCATION: Singapore", kwargs["user"])
        self.assertNotIn("APPLICANT LOCATION RESTRICTION", kwargs["user"])

    def test_residency_blocks_remote_and_unspecified_but_not_office_jobs(self):
        from jobs.consts import RemoteOption

        flag = {"residency_excludes_indonesia": True}
        self.assertFalse(self._check(RemoteOption.REMOTE, **flag)[0].is_relevant)
        self.assertFalse(self._check(None, **flag)[0].is_relevant)
        self.assertTrue(self._check(RemoteOption.ON_SITE, **flag)[0].is_relevant)
        self.assertTrue(self._check(RemoteOption.HYBRID, **flag)[0].is_relevant)

    def test_foreign_work_authorization_blocks_every_job(self):
        from jobs.consts import RemoteOption

        flag = {"requires_foreign_work_authorization": True}
        for ro in (RemoteOption.REMOTE, RemoteOption.ON_SITE, None):
            self.assertFalse(self._check(ro, **flag)[0].is_relevant)

    def test_field_mismatch_blocks(self):
        from jobs.consts import RemoteOption

        self.assertFalse(
            self._check(RemoteOption.ON_SITE, same_field=False)[0].is_relevant
        )


_BODY = (
    "We are hiring a backend engineer to build Python/Django APIs, design "
    "Postgres schemas, and ship features with a small product team. "
)


@skipUnless(settings.OPENAI_API_KEY, "needs OPENAI_API_KEY (real gpt-4o-mini calls)")
class RelevanceGateLiveTests(SimpleTestCase):
    """Guards RELEVANCE_SYSTEM_PROMPT against the real model, which mocks can't.

    Runs in the regular suite whenever OPENAI_API_KEY is set (~10 cheap
    gpt-4o-mini calls). A failure after a prompt/model change means the
    country or field rule regressed. The model is nondeterministic, so a rare
    one-off flake is possible (50/50 correct across 5 runs when written).
    """

    PREF = SimpleNamespace(title="Software Engineer", job_type=[], remote_option=[])

    def _assert_all(self, expected, cases):
        from assessment.services import check_relevance

        for name, title, location, remote_option, description in cases:
            with self.subTest(case=name):
                job = Job(
                    url="https://x",
                    title=title,
                    company="Acme",
                    location=location,
                    remote_option=remote_option,
                    description=description,
                )
                result = check_relevance(job, self.PREF)
                self.assertEqual(result.is_relevant, expected, result.reason)

    def test_not_open_to_indonesia_is_filtered(self):
        self._assert_all(
            False,
            [
                ("remote US-only list", "Backend Engineer", "United States", "remote", _BODY),
                ("US work authorization", "Backend Engineer", "Remote", "remote",
                 _BODY + "Candidates must be authorized to work in the US. We do not sponsor visas."),
                ("UK right to work", "Backend Engineer", "London, England", "remote",
                 _BODY + "You must have the right to work in the UK."),
                ("restriction at description tail", "Backend Engineer", None, "remote",
                 _BODY * 25 + "This position is open to residents of Canada only."),
            ],
        )  # fmt: skip

    def test_open_to_indonesia_passes(self):
        self._assert_all(
            True,
            [
                ("remote worldwide", "Backend Engineer", "Worldwide", "remote", _BODY),
                ("remote list with Indonesia", "Backend Engineer",
                 "Indonesia, Malaysia, Philippines", "remote", _BODY),
                ("remote APAC", "Backend Engineer", "APAC", "remote", _BODY),
                ("on-site office abroad", "Backend Engineer", "Singapore", "on-site",
                 _BODY + "Work from our Singapore office."),
                ("timezone overlap only", "Backend Engineer", "Worldwide", "remote",
                 _BODY + "Must overlap at least 4 hours with US Eastern time."),
            ],
        )  # fmt: skip

    def test_field_mismatch_is_filtered(self):
        self._assert_all(
            False,
            [("housekeeper", "Housekeeper", "Jakarta", "on-site", "Clean hotel rooms daily.")],
        )  # fmt: skip
