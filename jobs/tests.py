from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from jobs.scrapers import dealls, indeed, jobstreet, linkedin, scraper_for_url
from jobs.url_builders import build_crawl_urls, build_jobstreet_url, build_linkedin_url

FIXTURES = Path(__file__).parent / "fixtures_html"
LISTING_HTML = (FIXTURES / "listing.html").read_text()
DETAIL_HTML = (FIXTURES / "detail.html").read_text()
LI_LISTING_HTML = (FIXTURES / "linkedin_listing.html").read_text()
LI_DETAIL_HTML = (FIXTURES / "linkedin_detail.html").read_text()
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

    def test_extracts_link_with_new_path_format(self):
        # Regression: JobStreet listings now serve /job/<id> (no /id/ prefix).
        html = '<a href="/job/12345?type=standard&origin=cardTitle">Job</a>'
        urls = jobstreet.parse_listing(html)
        self.assertEqual(
            urls,
            [
                "https://id.jobstreet.com/id/job/12345?type=standard&ref=search-standalone"
            ],
        )

    def test_extracts_link_with_legacy_path_format(self):
        html = '<a href="/id/job/12345?type=standard">Job</a>'
        urls = jobstreet.parse_listing(html)
        self.assertEqual(
            urls,
            [
                "https://id.jobstreet.com/id/job/12345?type=standard&ref=search-standalone"
            ],
        )


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


class LinkedInGuestSearchUrlTests(TestCase):
    INPUT = (
        "https://www.linkedin.com/jobs/search/?geoId=91000014&keywords=flutter"
        "&origin=JOBS_HOME_LOCATION_HISTORY&position=1&pageNum=0&currentJobId=4419429587"
        "&f_WT=2"
    )

    def test_keeps_search_params_drops_ui_cruft(self):
        out = linkedin._guest_search_url(self.INPUT, 0)
        self.assertTrue(out.startswith(linkedin.GUEST_SEARCH))
        self.assertIn("keywords=flutter", out)
        self.assertIn("geoId=91000014", out)
        self.assertIn("f_WT=2", out)
        self.assertIn("start=0", out)
        for cruft in ("origin=", "position=", "pageNum=", "currentJobId="):
            self.assertNotIn(cruft, out)

    def test_start_steps_by_ten(self):
        pages = list(linkedin.iter_listing_pages(self.INPUT, 3))
        self.assertEqual(len(pages), 3)
        self.assertIn("start=0", pages[0])
        self.assertIn("start=10", pages[1])
        self.assertIn("start=20", pages[2])


class LinkedInParseListingTests(TestCase):
    def test_returns_card_dicts(self):
        cards = linkedin.parse_listing(LI_LISTING_HTML)
        self.assertGreater(len(cards), 0)
        ids = [c["job_id"] for c in cards]
        self.assertEqual(len(ids), len(set(ids)))
        first = cards[0]
        self.assertEqual(first["job_id"], "4419429587")
        self.assertEqual(first["title"], "Flutter")
        self.assertEqual(first["company"], "AARVY TECHNOLOGIES")
        self.assertTrue(first["url"].endswith("4419429587"))


class LinkedInParseDetailTests(TestCase):
    BASE = {
        "url": "https://id.linkedin.com/jobs/view/flutter-4419429587",
        "job_id": "4419429587",
        "title": "Flutter",
        "company": "AARVY TECHNOLOGIES",
        "location": "Lembang",
    }

    def test_merges_description_and_job_type(self):
        result = linkedin.parse_detail(LI_DETAIL_HTML, dict(self.BASE))
        self.assertIsNotNone(result)
        self.assertEqual(result["url"], self.BASE["url"])
        self.assertEqual(result["title"], "Flutter")
        self.assertIn("Salary", result["description"])
        # Localized "Penuh waktu" criteria value maps to FULL_TIME.
        self.assertEqual(result["job_type"], JobType.FULL_TIME)

    def test_returns_none_without_description(self):
        self.assertIsNone(linkedin.parse_detail("<html></html>", dict(self.BASE)))


class LinkedInEmploymentTypeTests(TestCase):
    def test_english_and_indonesian_values(self):
        self.assertEqual(
            linkedin._employment_type_from_criteria(["Tidak Berlaku", "Penuh waktu"]),
            JobType.FULL_TIME,
        )
        self.assertEqual(
            linkedin._employment_type_from_criteria(["Full-time"]), JobType.FULL_TIME
        )
        self.assertEqual(
            linkedin._employment_type_from_criteria(["Magang"]), JobType.INTERNSHIP
        )
        self.assertIsNone(linkedin._employment_type_from_criteria(["Lainnya"]))


class _LiResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200
        self.url = ""

    def raise_for_status(self):
        pass


def _li_stub_get(self, url, *args, **kwargs):
    resp = _LiResp(LI_DETAIL_HTML if "/jobPosting/" in url else LI_LISTING_HTML)
    resp.url = url
    return resp


class LinkedInCommandTests(TestCase):
    URL = "https://www.linkedin.com/jobs/search/?keywords=flutter&geoId=102478259"

    @patch("curl_cffi.requests.Session.get", new=_li_stub_get)
    @patch("jobs.scrapers.linkedin.time.sleep", lambda *_: None)
    def test_dry_run_does_not_write(self):
        out = io.StringIO()
        call_command(
            "crawl_linkedin", self.URL, "--limit", "2", "--dry-run", stdout=out
        )
        self.assertEqual(Job.objects.count(), 0)
        self.assertIn("AARVY TECHNOLOGIES", out.getvalue())

    @patch("curl_cffi.requests.Session.get", new=_li_stub_get)
    @patch("jobs.scrapers.linkedin.time.sleep", lambda *_: None)
    def test_writes_and_is_idempotent(self):
        call_command("crawl_linkedin", self.URL, "--limit", "2")
        first_count = Job.objects.count()
        self.assertGreater(first_count, 0)
        self.assertTrue(Job.objects.filter(source="linkedin").exists())
        call_command("crawl_linkedin", self.URL, "--limit", "2")
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

    def test_linkedin_host(self):
        for url in (
            "https://www.linkedin.com/jobs/search/?keywords=flutter",
            "https://id.linkedin.com/jobs/view/flutter-4419429587",
        ):
            scraper, source = scraper_for_url(url)
            self.assertIs(scraper, linkedin)
            self.assertEqual(source, "linkedin")

    def test_dealls_host(self):
        for url in (
            "https://dealls.com/?location=remote&employment=partTime",
            "https://www.dealls.com/loker/brand-officer-5~kunkwan-mandarin",
        ):
            scraper, source = scraper_for_url(url)
            self.assertIs(scraper, dealls)
            self.assertEqual(source, "dealls")

    def test_unknown_host(self):
        self.assertEqual(scraper_for_url("https://example.com/jobs"), (None, None))

    def test_malformed_url(self):
        self.assertEqual(scraper_for_url(""), (None, None))
        self.assertEqual(scraper_for_url("not a url"), (None, None))


# --- Dealls (JSON API) -------------------------------------------------------

DEALLS_URL = (
    "https://dealls.com/?location=remote&employment=partTime&employment=freelance"
)

# Trimmed shape of a real ``data.result`` object from
# api.sejutacita.id/v1/job-portal/job/slug/<slug>?guest=true
DEALLS_RESULT = {
    "slug": "brand-officer-5",
    "role": "Brand Officer",
    "description": None,
    "responsibilities": "<p><strong>Tanggung Jawab</strong></p><ul><li>Promosi produk.</li></ul>",
    "requirements": "<ul><li>Komunikatif dan ramah.</li></ul>",
    "employmentTypes": ["freelance"],
    "workplaceType": "remote",
    "location": None,
    "company": {
        "name": "PT. KUNKWAN MANDARIN INDONESIA",
        "slug": "kunkwan-mandarin",
        "location": {"city": {"id": 158, "name": "Jakarta Selatan"}},
    },
}


class DeallsListApiUrlTests(TestCase):
    def test_translates_location_and_employment(self):
        url = dealls._list_api_url(DEALLS_URL, page=2)
        self.assertTrue(url.startswith(dealls.LIST_API + "?"))
        query = url.split("?", 1)[1]
        self.assertIn("page=2", query)
        self.assertIn(f"limit={dealls.PAGE_LIMIT}", query)
        self.assertIn("published=true", query)
        self.assertIn("status=active", query)
        # employment -> employmentTypes[i] (order preserved); [ ] are url-encoded
        self.assertIn("employmentTypes%5B0%5D=partTime", query)
        self.assertIn("employmentTypes%5B1%5D=freelance", query)
        # location -> workplaceTypes[i]
        self.assertIn("workplaceTypes%5B0%5D=remote", query)

    def test_no_filters_still_valid(self):
        url = dealls._list_api_url("https://dealls.com/", page=1)
        query = url.split("?", 1)[1]
        self.assertIn("page=1", query)
        self.assertNotIn("employmentTypes", query)
        self.assertNotIn("workplaceTypes", query)


class DeallsParseListingTests(TestCase):
    def test_extracts_unique_slugs(self):
        payload = {"data": {"docs": [{"slug": "a"}, {"slug": "b"}, {"slug": "a"}, {}]}}
        self.assertEqual(dealls.parse_listing(payload), ["a", "b"])

    def test_empty_payload(self):
        self.assertEqual(dealls.parse_listing({}), [])


class DeallsParseDetailTests(TestCase):
    def test_returns_expected_fields(self):
        result = dealls.parse_detail(DEALLS_RESULT)
        self.assertEqual(
            result["url"], "https://dealls.com/loker/brand-officer-5~kunkwan-mandarin"
        )
        self.assertEqual(result["title"], "Brand Officer")
        self.assertEqual(result["company"], "PT. KUNKWAN MANDARIN INDONESIA")
        # HTML stripped, both sections concatenated
        self.assertIn("Promosi produk.", result["description"])
        self.assertIn("Komunikatif dan ramah.", result["description"])
        self.assertNotIn("<li>", result["description"])
        # freelance -> PART_TIME (product decision), remote -> REMOTE
        self.assertEqual(result["job_type"], JobType.PART_TIME)
        self.assertEqual(result["remote_option"], RemoteOption.REMOTE)
        # location falls back to company city when job location is null
        self.assertEqual(result["location"], "Jakarta Selatan")

    def test_prefers_job_location_over_company(self):
        result = dealls.parse_detail(
            {**DEALLS_RESULT, "location": {"city": {"name": "Surabaya"}}}
        )
        self.assertEqual(result["location"], "Surabaya")

    def test_onsite_maps_to_on_site(self):
        result = dealls.parse_detail({**DEALLS_RESULT, "workplaceType": "onSite"})
        self.assertEqual(result["remote_option"], RemoteOption.ON_SITE)

    def test_url_without_company_slug(self):
        company = {**DEALLS_RESULT["company"], "slug": None}
        result = dealls.parse_detail({**DEALLS_RESULT, "company": company})
        self.assertEqual(result["url"], "https://dealls.com/loker/brand-officer-5")

    def test_returns_none_without_description(self):
        barren = {
            **DEALLS_RESULT,
            "description": None,
            "responsibilities": None,
            "requirements": None,
        }
        self.assertIsNone(dealls.parse_detail(barren))


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


class BuildLinkedInUrlTests(TestCase):
    def test_title_only(self):
        url = build_linkedin_url("Mobile Developer")
        self.assertTrue(url.startswith("https://www.linkedin.com/jobs/search/?"))
        self.assertIn("keywords=Mobile+Developer", url)
        self.assertIn("geoId=91000014", url)

    def test_job_type_and_remote_filters(self):
        url = build_linkedin_url(
            "Mobile Developer", [JobType.FULL_TIME], [RemoteOption.REMOTE]
        )
        self.assertIn("f_JT=F", url)
        self.assertIn("f_WT=2", url)

    def test_unknown_values_dropped(self):
        url = build_linkedin_url("Dev", ["bogus"], ["nope"])
        self.assertNotIn("f_JT=", url)
        self.assertNotIn("f_WT=", url)

    def test_empty_title_returns_none(self):
        self.assertIsNone(build_linkedin_url(""))
        self.assertIsNone(build_linkedin_url(None))
        self.assertIsNone(build_linkedin_url("   "))

    def test_round_trips_through_scraper_for_url(self):
        url = build_linkedin_url("Mobile Developer", [JobType.CONTRACT])
        scraper, source = scraper_for_url(url)
        self.assertIs(scraper, linkedin)
        self.assertEqual(source, "linkedin")


class BuildCrawlUrlsTests(TestCase):
    def test_includes_indeed_jobstreet_and_linkedin(self):
        urls = build_crawl_urls("Mobile Developer")
        self.assertEqual(len(urls), 3)
        hosts = [scraper_for_url(u)[1] for u in urls]
        self.assertEqual(hosts, ["indeed", "jobstreet", "linkedin"])

    def test_empty_title_returns_empty(self):
        self.assertEqual(build_crawl_urls(""), [])


class ExtractJobSkillsTaskTests(TestCase):
    def _make_job(self, **kwargs):
        defaults = dict(
            url="https://id.indeed.com/viewjob?jk=skilltest",
            title="Backend Engineer",
            description="We need Python and Django experience plus teamwork.",
        )
        defaults.update(kwargs)
        return Job.objects.create(**defaults)

    @patch("jobs.tasks.extract_skills")
    def test_fills_skills_from_llm(self, mock_extract):
        from jobs.services import JobSkills

        mock_extract.return_value = JobSkills(
            hard_skills=["Python", "Django"], soft_skills=["teamwork"]
        )
        job = self._make_job()

        from jobs.tasks import extract_job_skills

        result = extract_job_skills(job.id)

        self.assertEqual(result, "extracted")
        job.refresh_from_db()
        self.assertEqual(job.hard_skills, ["Python", "Django"])
        self.assertEqual(job.soft_skills, ["teamwork"])
        mock_extract.assert_called_once()

    @patch("jobs.tasks.extract_skills")
    def test_skips_when_already_filled(self, mock_extract):
        job = self._make_job(hard_skills=["Go"])

        from jobs.tasks import extract_job_skills

        result = extract_job_skills(job.id)

        self.assertEqual(result, "skipped")
        mock_extract.assert_not_called()
