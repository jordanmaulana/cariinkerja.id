from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

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


def _make_job(slug: str) -> Job:
    return Job.objects.create(
        url=f"https://job.test/{slug}",
        title="Senior Dev",
        description="x",
        location="Jakarta",
        source="jobstreet",
    )


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
