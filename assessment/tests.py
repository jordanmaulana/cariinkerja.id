from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from assessment.tasks import (
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
