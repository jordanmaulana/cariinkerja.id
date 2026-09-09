from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from profiles.consts import Status as PrefStatus
from profiles.models import Preference, Profile

User = get_user_model()

# The default manifest storage demands a built static manifest (output.css),
# which the test env has no reason to produce.
NO_MANIFEST_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)


@NO_MANIFEST_STATICFILES
class PreferenceCrawlNowViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@x.com", password="x"
        )
        u = User.objects.create_user(username="u", email="u@x.com", password="x")
        self.profile = Profile.objects.create(user=u)
        self.pref = Preference.objects.create(
            profile=self.profile,
            title="Senior Dev",
            status=PrefStatus.RUNNING,
            crawl_urls=["https://listing.test/q=dev"],
        )
        self.url = reverse("preference_crawl_now", kwargs={"pk": self.pref.pk})

    def test_queues_crawl_with_reassess_opted_in(self):
        self.client.force_login(self.admin)
        with patch("core.views.crawl_and_assess_preference.delay") as m:
            resp = self.client.post(self.url)
        self.assertRedirects(
            resp, reverse("preference_detail", kwargs={"pk": self.pref.pk})
        )
        m.assert_called_once_with(self.pref.id, reassess_existing=True)

    def test_empty_crawl_urls_does_not_queue(self):
        self.pref.crawl_urls = []
        self.pref.save(update_fields=["crawl_urls", "updated_on"])
        self.client.force_login(self.admin)
        with patch("core.views.crawl_and_assess_preference.delay") as m:
            resp = self.client.post(self.url, follow=True)
        m.assert_not_called()
        self.assertContains(resp, "no crawl_urls")

    def test_requires_superuser(self):
        self.client.force_login(
            User.objects.create_user(username="plain", email="p@x.com", password="x")
        )
        with patch("core.views.crawl_and_assess_preference.delay") as m:
            resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])
        m.assert_not_called()


@NO_MANIFEST_STATICFILES
class PreferenceRegenerateUrlsViewTests(TestCase):
    """The two admin regenerate flows must emit the clean-source set only.

    Both views call `build_crawl_urls`, so this is the end-to-end guard that a
    legacy board cannot come back through an admin action.
    """

    LEGACY_HOSTS = ("indeed.com", "jobstreet.com", "linkedin.com")

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@x.com", password="x"
        )
        self.profile = Profile.objects.create(full_name="Cody")
        # Seeded with the pre-2026-09-09 set, as a legacy row would be.
        self.pref = Preference.objects.create(
            profile=self.profile,
            title="Mobile Developer",
            status=PrefStatus.RUNNING,
            crawl_urls=[
                "https://id.indeed.com/jobs?q=Mobile+Developer",
                "https://id.jobstreet.com/mobile-developer-jobs",
            ],
        )
        self.client.force_login(self.admin)

    def _assert_clean(self, pref):
        pref.refresh_from_db()
        self.assertEqual(len(pref.crawl_urls), 3)
        joined = " ".join(pref.crawl_urls)
        for host in self.LEGACY_HOSTS:
            self.assertNotIn(host, joined)

    def test_single_regenerate_drops_legacy_urls(self):
        resp = self.client.post(
            reverse("preference_regenerate_urls", kwargs={"pk": self.pref.pk})
        )
        self.assertRedirects(
            resp, reverse("preference_detail", kwargs={"pk": self.pref.pk})
        )
        self._assert_clean(self.pref)

    def test_regenerate_all_drops_legacy_urls(self):
        other = Preference.objects.create(
            profile=self.profile,
            title="Backend Engineer",
            status=PrefStatus.RUNNING,
            crawl_urls=["https://www.linkedin.com/jobs/search/?keywords=Backend"],
        )
        resp = self.client.post(reverse("preference_regenerate_all_urls"))
        self.assertRedirects(resp, reverse("preference_list"))
        self._assert_clean(self.pref)
        self._assert_clean(other)
