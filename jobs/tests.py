from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from jobs.scrapers import indeed, jobstreet, scraper_for_url
from jobs.url_builders import build_jobstreet_url

FIXTURES = Path(__file__).parent / "fixtures_html"
LISTING_HTML = (FIXTURES / "listing.html").read_text()
DETAIL_HTML = (FIXTURES / "detail.html").read_text()
DETAIL_URL = (
    "https://id.jobstreet.com/id/job/91819691?type=standard&ref=search-standalone"
)


class IterListingPagesTests(TestCase):
    def test_first_page_is_input_url(self):
        pages = list(
            jobstreet.iter_listing_pages(
                "https://id.jobstreet.com/id/mobile-jobs/part-time/remote", 1
            )
        )
        self.assertEqual(
            pages, ["https://id.jobstreet.com/id/mobile-jobs/part-time/remote"]
        )

    def test_appends_page_query_param(self):
        pages = list(
            jobstreet.iter_listing_pages(
                "https://id.jobstreet.com/id/mobile-jobs/part-time/remote", 3
            )
        )
        self.assertEqual(len(pages), 3)
        self.assertIn("page=2", pages[1])
        self.assertIn("page=3", pages[2])

    def test_replaces_existing_page_param(self):
        pages = list(
            jobstreet.iter_listing_pages(
                "https://id.jobstreet.com/id/mobile-jobs/part-time/remote?page=5&q=foo",
                2,
            )
        )
        self.assertIn("q=foo", pages[1])
        self.assertIn("page=2", pages[1])
        self.assertNotIn("page=5", pages[1])


class ParseListingTests(TestCase):
    def test_extracts_unique_job_urls(self):
        urls = jobstreet.parse_listing(LISTING_HTML)
        self.assertGreater(len(urls), 0)
        self.assertEqual(len(urls), len(set(urls)))
        for u in urls:
            self.assertTrue(u.startswith("https://id.jobstreet.com/id/job/"))


class ParseDetailTests(TestCase):
    def test_returns_expected_fields(self):
        result = jobstreet.parse_detail(DETAIL_HTML, DETAIL_URL)
        self.assertIsNotNone(result)
        self.assertEqual(result["url"], DETAIL_URL)
        self.assertEqual(result["title"], "Freelance Mandarin Curriculum Developer")
        self.assertIn("Mandarin", result["description"])
        self.assertEqual(result["location"], "Jakarta Barat, Jakarta Raya")
        self.assertEqual(result["job_type"], JobType.PART_TIME)
        self.assertEqual(result["remote_option"], RemoteOption.REMOTE)

    def test_returns_none_for_non_detail_page(self):
        self.assertIsNone(jobstreet.parse_detail("<html></html>", DETAIL_URL))


class LabelMappersTests(TestCase):
    def test_job_type_indonesian_and_english(self):
        self.assertEqual(jobstreet._map_job_type("Paruh waktu"), JobType.PART_TIME)
        self.assertEqual(jobstreet._map_job_type("Full Time"), JobType.FULL_TIME)
        self.assertEqual(jobstreet._map_job_type("Magang"), JobType.INTERNSHIP)
        self.assertIsNone(jobstreet._map_job_type("nonsense label"))

    def test_remote_from_location_paren(self):
        self.assertEqual(
            jobstreet._map_remote_option("Jakarta (Jarak jauh)", ""),
            RemoteOption.REMOTE,
        )
        self.assertEqual(
            jobstreet._map_remote_option("Jakarta (Hibrid)", ""),
            RemoteOption.HYBRID,
        )
        self.assertIsNone(jobstreet._map_remote_option("Jakarta", ""))


class _StubResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200
        self.request = None

    def raise_for_status(self):
        pass


def _stub_get(self, url, *args, **kwargs):
    if "/id/job/" in url:
        return _StubResp(DETAIL_HTML)
    return _StubResp(LISTING_HTML)


class CommandTests(TestCase):
    URL = "https://id.jobstreet.com/id/mobile-jobs/part-time/remote"

    @patch("httpx.Client.get", new=_stub_get)
    @patch("jobs.scrapers.jobstreet.time.sleep", lambda *_: None)
    def test_dry_run_does_not_write(self):
        out = io.StringIO()
        call_command(
            "crawl_jobstreet",
            self.URL,
            "--max-pages",
            "1",
            "--limit",
            "2",
            "--dry-run",
            stdout=out,
        )
        self.assertEqual(Job.objects.count(), 0)
        self.assertIn("Freelance Mandarin Curriculum Developer", out.getvalue())

    @patch("httpx.Client.get", new=_stub_get)
    @patch("jobs.scrapers.jobstreet.time.sleep", lambda *_: None)
    def test_writes_and_is_idempotent(self):
        call_command("crawl_jobstreet", self.URL, "--max-pages", "1", "--limit", "2")
        first_count = Job.objects.count()
        self.assertGreater(first_count, 0)
        job = Job.objects.first()
        self.assertEqual(job.job_type, JobType.PART_TIME)
        self.assertEqual(job.remote_option, RemoteOption.REMOTE)

        call_command("crawl_jobstreet", self.URL, "--max-pages", "1", "--limit", "2")
        self.assertEqual(Job.objects.count(), first_count)


class ScraperForUrlTests(TestCase):
    def test_indeed_host(self):
        scraper, source = scraper_for_url("https://id.indeed.com/jobs?q=python")
        self.assertIs(scraper, indeed)
        self.assertEqual(source, "indeed")

    def test_jobstreet_host(self):
        scraper, source = scraper_for_url("https://id.jobstreet.com/jobs/foo")
        self.assertIs(scraper, jobstreet)
        self.assertEqual(source, "jobstreet")

    def test_unknown_host(self):
        self.assertEqual(scraper_for_url("https://example.com/jobs"), (None, None))

    def test_malformed_url(self):
        self.assertEqual(scraper_for_url(""), (None, None))
        self.assertEqual(scraper_for_url("not a url"), (None, None))


class BuildJobstreetUrlTests(TestCase):
    BASE = "https://id.jobstreet.com/mobile-developer-jobs"

    def test_title_only(self):
        self.assertEqual(build_jobstreet_url("Mobile Developer"), self.BASE)

    def test_single_full_time(self):
        self.assertEqual(
            build_jobstreet_url("Mobile Developer", [JobType.FULL_TIME]),
            f"{self.BASE}/full-time",
        )

    def test_single_part_time(self):
        self.assertEqual(
            build_jobstreet_url("Mobile Developer", [JobType.PART_TIME]),
            f"{self.BASE}/part-time",
        )

    def test_single_contract_uses_temp_slug(self):
        self.assertEqual(
            build_jobstreet_url("Mobile Developer", [JobType.CONTRACT]),
            f"{self.BASE}/contract-temp",
        )

    def test_single_internship_uses_casual_vacation_slug(self):
        self.assertEqual(
            build_jobstreet_url("Mobile Developer", [JobType.INTERNSHIP]),
            f"{self.BASE}/casual-vacation",
        )

    def test_multi_job_type_uses_worktype_query_param(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer", [JobType.FULL_TIME, JobType.PART_TIME]
            ),
            f"{self.BASE}?worktype=242%2C243",
        )

    def test_remote_only_uses_workarrangement_query_param(self):
        self.assertEqual(
            build_jobstreet_url("Mobile Developer", None, [RemoteOption.ON_SITE]),
            f"{self.BASE}?workarrangement=2",
        )

    def test_multi_remote_only(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer",
                None,
                [RemoteOption.HYBRID, RemoteOption.ON_SITE],
            ),
            f"{self.BASE}?workarrangement=1%2C2",
        )

    def test_single_jt_single_ro(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer", [JobType.FULL_TIME], [RemoteOption.ON_SITE]
            ),
            f"{self.BASE}/full-time/on-site",
        )

    def test_single_jt_multi_ro(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer",
                [JobType.FULL_TIME],
                [RemoteOption.HYBRID, RemoteOption.ON_SITE],
            ),
            f"{self.BASE}/full-time?workarrangement=1%2C2",
        )

    def test_multi_jt_single_ro(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer",
                [JobType.FULL_TIME, JobType.PART_TIME],
                [RemoteOption.ON_SITE],
            ),
            f"{self.BASE}?worktype=242%2C243&workarrangement=2",
        )

    def test_multi_jt_multi_ro(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer",
                [JobType.FULL_TIME, JobType.CONTRACT],
                [RemoteOption.REMOTE, RemoteOption.HYBRID],
            ),
            f"{self.BASE}?worktype=242%2C244&workarrangement=3%2C1",
        )

    def test_empty_title_returns_none(self):
        self.assertIsNone(build_jobstreet_url(""))
        self.assertIsNone(build_jobstreet_url(None))
        self.assertIsNone(build_jobstreet_url("   "))

    def test_emoji_only_title_returns_none(self):
        self.assertIsNone(build_jobstreet_url("🚀✨"))

    def test_non_ascii_title_is_normalized(self):
        self.assertEqual(
            build_jobstreet_url("Sénior Developer"),
            "https://id.jobstreet.com/senior-developer-jobs",
        )

    def test_unknown_values_are_dropped(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer", ["bogus", JobType.FULL_TIME], ["unknown"]
            ),
            f"{self.BASE}/full-time",
        )

    def test_duplicates_are_deduped_preserving_order(self):
        self.assertEqual(
            build_jobstreet_url(
                "Mobile Developer",
                [JobType.PART_TIME, JobType.FULL_TIME, JobType.PART_TIME],
            ),
            f"{self.BASE}?worktype=243%2C242",
        )

    def test_long_title_is_truncated_on_hyphen(self):
        title = "Senior " * 30 + "Developer"
        url = build_jobstreet_url(title)
        slug = url.removeprefix("https://id.jobstreet.com/").removesuffix("-jobs")
        self.assertLessEqual(len(slug), 80)
        self.assertFalse(slug.endswith("-"))

    def test_round_trips_through_scraper_for_url(self):
        for jts, ros in [
            (None, None),
            ([JobType.FULL_TIME], None),
            ([JobType.FULL_TIME, JobType.PART_TIME], [RemoteOption.HYBRID]),
            (None, [RemoteOption.REMOTE]),
        ]:
            url = build_jobstreet_url("Mobile Developer", jts, ros)
            scraper, source = scraper_for_url(url)
            self.assertIs(scraper, jobstreet)
            self.assertEqual(source, "jobstreet")
