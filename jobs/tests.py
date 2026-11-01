from __future__ import annotations

import io
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from jobs.scrapers import (
    dealls,
    himalayas,
    jobicy,
    linkedin,
    remoteok,
    scraper_for_url,
    workable,
)
from jobs.url_builders import (
    LINKEDIN_GEOID_EMEA,
    build_crawl_urls,
    build_himalayas_url,
    build_jobicy_url,
    build_linkedin_url,
    build_remoteok_url,
    build_workable_url,
)

FIXTURES = Path(__file__).parent / "fixtures_html"
LI_LISTING_HTML = (FIXTURES / "linkedin_listing.html").read_text()
LI_DETAIL_HTML = (FIXTURES / "linkedin_detail.html").read_text()


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
    def test_removed_indeed_and_jobstreet_hosts_are_unknown(self):
        for url in (
            "https://id.indeed.com/jobs?q=python",
            "https://id.jobstreet.com/jobs/foo",
        ):
            self.assertEqual(scraper_for_url(url), (None, None))

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

    def test_himalayas_host(self):
        scraper, source = scraper_for_url(
            "https://himalayas.app/jobs/api/search?q=flutter"
        )
        self.assertIs(scraper, himalayas)
        self.assertEqual(source, "himalayas")

    def test_jobicy_host(self):
        scraper, source = scraper_for_url("https://jobicy.com/api/jobs?tag=flutter")
        self.assertIs(scraper, jobicy)
        self.assertEqual(source, "jobicy")

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

    def test_geo_id_override_emits_that_region(self):
        url = build_linkedin_url("Mobile Developer", geo_id=LINKEDIN_GEOID_EMEA)
        self.assertIn("geoId=91000007", url)
        self.assertNotIn("geoId=91000014", url)


class BuildCrawlUrlsTests(TestCase):
    def test_includes_linkedin_and_remote_boards(self):
        urls = build_crawl_urls("Mobile Developer")
        self.assertEqual(len(urls), 5)
        hosts = [scraper_for_url(u)[1] for u in urls]
        self.assertEqual(
            hosts,
            [
                "linkedin",
                "himalayas",
                "jobicy",
                "workable",
                "remoteok",
            ],
        )

    def test_non_remote_preference_omits_emea(self):
        urls = build_crawl_urls("Mobile Developer", None, [RemoteOption.ON_SITE])
        self.assertEqual(len(urls), 5)
        self.assertNotIn("geoId=91000007", " ".join(urls))

    def test_remote_preference_appends_emea_linkedin(self):
        urls = build_crawl_urls("Mobile Developer", None, [RemoteOption.REMOTE])
        self.assertEqual(len(urls), 6)
        emea = urls[1]
        self.assertIn("geoId=91000007", emea)
        self.assertIn("f_WT=2", emea)
        scraper, source = scraper_for_url(emea)
        self.assertIs(scraper, linkedin)
        self.assertEqual(source, "linkedin")

    def test_remote_boards_always_appended_last(self):
        for ros in (None, [RemoteOption.ON_SITE], [RemoteOption.REMOTE]):
            urls = build_crawl_urls("Mobile Developer", [JobType.FULL_TIME], ros)
            self.assertEqual(
                urls[-4:],
                [
                    build_himalayas_url("Mobile Developer", [JobType.FULL_TIME]),
                    build_jobicy_url("Mobile Developer"),
                    build_workable_url("Mobile Developer"),
                    build_remoteok_url("Mobile Developer"),
                ],
            )

    def test_empty_title_returns_empty(self):
        self.assertEqual(build_crawl_urls(""), [])


class BuildHimalayasUrlTests(TestCase):
    BASE = "https://himalayas.app/jobs/api/search"

    def test_title_only_has_no_country_filter(self):
        self.assertEqual(
            build_himalayas_url("Mobile Developer"), f"{self.BASE}?q=Mobile+Developer"
        )

    def test_job_types_comma_joined(self):
        self.assertEqual(
            build_himalayas_url(
                "Dev", [JobType.FULL_TIME, JobType.CONTRACT, JobType.INTERNSHIP]
            ),
            f"{self.BASE}?q=Dev&employment_type=Full+Time%2CContractor%2CTemporary%2CIntern",
        )

    def test_unknown_and_duplicate_values_dropped(self):
        self.assertEqual(
            build_himalayas_url("Dev", ["bogus", JobType.PART_TIME, JobType.PART_TIME]),
            f"{self.BASE}?q=Dev&employment_type=Part+Time",
        )

    def test_empty_title_returns_none(self):
        self.assertIsNone(build_himalayas_url(""))
        self.assertIsNone(build_himalayas_url(None))
        self.assertIsNone(build_himalayas_url("   "))

    def test_round_trips_through_scraper_for_url(self):
        scraper, source = scraper_for_url(
            build_himalayas_url("Dev", [JobType.FULL_TIME])
        )
        self.assertIs(scraper, himalayas)
        self.assertEqual(source, "himalayas")


# --- Himalayas (JSON API) ----------------------------------------------------

HIMALAYAS_URL = "https://himalayas.app/jobs/api/search?q=flutter"


def _himalayas_job(guid="g1", expiry_delta=timedelta(days=10), **overrides):
    """Trimmed shape of a real job object from himalayas.app/jobs/api/search."""
    job = {
        "title": "Senior Flutter Developer",
        "excerpt": "Short excerpt.",
        "companyName": "Somnio Software",
        "employmentType": "Contractor",
        "locationRestrictions": [],
        "description": "<p>Build <strong>apps</strong>.</p><ul><li>Dart</li></ul>",
        "expiryDate": int((timezone.now() + expiry_delta).timestamp()),
        "applicationLink": f"https://himalayas.app/companies/somnio/jobs/{guid}?utm_source=api",
        "guid": f"https://himalayas.app/companies/somnio/jobs/{guid}",
    }
    job.update(overrides)
    return job


class HimalayasParseJobTests(TestCase):
    def test_maps_fields(self):
        job = _himalayas_job(locationRestrictions=["Indonesia", "Malaysia"])
        out = himalayas.parse_job(job)
        self.assertEqual(out["url"], job["applicationLink"])  # ToS: unchanged
        self.assertEqual(out["title"], "Senior Flutter Developer")
        self.assertEqual(out["company"], "Somnio Software")
        self.assertEqual(out["job_type"], JobType.CONTRACT)
        self.assertEqual(out["remote_option"], RemoteOption.REMOTE)
        self.assertEqual(out["location"], "Indonesia, Malaysia")
        self.assertIn("Build\napps", out["description"])
        self.assertNotIn("<", out["description"])
        self.assertEqual(int(out["expires_at"].timestamp()), job["expiryDate"])

    def test_indonesia_listed_first_so_truncation_keeps_it(self):
        countries = [f"Country{i:02d}" for i in range(60)] + ["Indonesia"]
        out = himalayas.parse_job(_himalayas_job(locationRestrictions=countries))
        self.assertTrue(out["location"].startswith("Indonesia, "))
        self.assertLessEqual(len(out["location"]), 255)

    def test_no_restrictions_is_worldwide(self):
        self.assertEqual(himalayas.parse_job(_himalayas_job())["location"], "Worldwide")

    def test_unmapped_employment_type_is_none(self):
        out = himalayas.parse_job(_himalayas_job(employmentType="Volunteer"))
        self.assertIsNone(out["job_type"])

    def test_missing_title_returns_none(self):
        self.assertIsNone(himalayas.parse_job(_himalayas_job(title="  ")))


class HimalayasCrawlTests(TestCase):
    def _crawl(self, pages, **kwargs):
        with patch.object(himalayas, "_request_json", side_effect=pages) as req:
            out = list(
                himalayas.crawl(HIMALAYAS_URL, client=object(), sleep=0, **kwargs)
            )
        return out, req

    def test_skips_expired_and_duplicate_jobs(self):
        page = {
            "jobs": [
                _himalayas_job("a"),
                _himalayas_job("a"),
                _himalayas_job("old", expiry_delta=timedelta(days=-1)),
                _himalayas_job("b"),
            ]
        }
        out, _ = self._crawl([page])
        self.assertEqual(
            [j["url"].split("/")[-1] for j in out],
            ["a?utm_source=api", "b?utm_source=api"],
        )

    def test_paginates_until_empty_page(self):
        out, req = self._crawl(
            [{"jobs": [_himalayas_job("a")]}, {"jobs": []}], max_pages=5
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(req.call_count, 2)
        self.assertIn("page=2", req.call_args_list[1].args[1])
        self.assertIn("q=flutter", req.call_args_list[1].args[1])

    def test_respects_limit(self):
        page = {"jobs": [_himalayas_job(str(i)) for i in range(5)]}
        out, _ = self._crawl([page], limit=2)
        self.assertEqual(len(out), 2)

    def test_listing_failure_does_not_raise(self):
        out, _ = self._crawl(RuntimeError("boom"))
        self.assertEqual(out, [])


class BuildJobicyUrlTests(TestCase):
    def test_title_with_apac_geo_and_count(self):
        self.assertEqual(
            build_jobicy_url(" Mobile Developer "),
            "https://jobicy.com/api/jobs?geo=apac&tag=Mobile+Developer&count=20",
        )

    def test_empty_title_returns_none(self):
        self.assertIsNone(build_jobicy_url(""))
        self.assertIsNone(build_jobicy_url(None))
        self.assertIsNone(build_jobicy_url("   "))

    def test_round_trips_through_scraper_for_url(self):
        scraper, source = scraper_for_url(build_jobicy_url("Dev"))
        self.assertIs(scraper, jobicy)
        self.assertEqual(source, "jobicy")


# --- Jobicy (JSON API) -------------------------------------------------------

JOBICY_URL = "https://jobicy.com/api/jobs?geo=apac&tag=flutter&count=20"


def _jobicy_job(job_id=1, **overrides):
    """Trimmed shape of a real job object from jobicy.com/api/jobs."""
    job = {
        "id": job_id,
        "url": f"https://jobicy.com/jobs/{job_id}-flutter-developer",
        "jobTitle": "Flutter Developer",
        "companyName": "Acme",
        "jobType": ["Full-Time"],
        "jobGeo": "Anywhere",
        "jobExcerpt": "Short excerpt&hellip;",
        "jobDescription": "<p>Build <strong>apps</strong>.</p><ul><li>Dart</li></ul>",
    }
    job.update(overrides)
    return job


class JobicyParseJobTests(TestCase):
    def test_maps_fields(self):
        job = _jobicy_job(jobType=["Contract"])
        out = jobicy.parse_job(job)
        self.assertEqual(out["url"], job["url"])  # ToS: apply via Jobicy URL
        self.assertEqual(out["title"], "Flutter Developer")
        self.assertEqual(out["company"], "Acme")
        self.assertEqual(out["job_type"], JobType.CONTRACT)
        self.assertEqual(out["remote_option"], RemoteOption.REMOTE)
        self.assertEqual(out["location"], "Anywhere")
        self.assertIn("Build\napps", out["description"])
        self.assertNotIn("<", out["description"])

    def test_geo_spacing_normalised(self):
        out = jobicy.parse_job(_jobicy_job(jobGeo="Canada,  USA"))
        self.assertEqual(out["location"], "Canada, USA")

    def test_missing_geo_is_anywhere(self):
        self.assertEqual(
            jobicy.parse_job(_jobicy_job(jobGeo=""))["location"], "Anywhere"
        )

    def test_unmapped_job_type_is_none(self):
        self.assertIsNone(
            jobicy.parse_job(_jobicy_job(jobType=["Volunteer"]))["job_type"]
        )

    def test_falls_back_to_excerpt(self):
        out = jobicy.parse_job(_jobicy_job(jobDescription=""))
        self.assertEqual(out["description"], "Short excerpt\u2026")

    def test_missing_title_returns_none(self):
        self.assertIsNone(jobicy.parse_job(_jobicy_job(jobTitle="  ")))


class JobicyCrawlTests(TestCase):
    def _crawl(self, pages, **kwargs):
        with patch.object(jobicy, "_request_json", side_effect=pages) as req:
            out = list(jobicy.crawl(JOBICY_URL, client=object(), sleep=0, **kwargs))
        return out, req

    def test_skips_duplicate_and_blocked_jobs(self):
        page = {
            "jobs": [
                _jobicy_job(1),
                _jobicy_job(1),
                _jobicy_job(2, companyName="Mindrift"),
                _jobicy_job(3),
            ],
            "hasMore": False,
        }
        out, _ = self._crawl([page])
        self.assertEqual(
            [j["url"].split("/")[-1].split("-")[0] for j in out], ["1", "3"]
        )

    def test_follows_cursor_until_no_more(self):
        out, req = self._crawl(
            [
                {"jobs": [_jobicy_job(1)], "hasMore": True, "nextCursor": "abc"},
                {"jobs": [_jobicy_job(2)], "hasMore": False, "nextCursor": None},
            ],
            max_pages=5,
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(req.call_count, 2)
        second = req.call_args_list[1].args[1]
        self.assertIn("cursor=abc", second)
        self.assertIn("tag=flutter", second)

    def test_single_page_by_default(self):
        out, req = self._crawl(
            [{"jobs": [_jobicy_job(1)], "hasMore": True, "nextCursor": "abc"}]
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(req.call_count, 1)

    def test_respects_limit(self):
        page = {"jobs": [_jobicy_job(i) for i in range(5)], "hasMore": False}
        out, _ = self._crawl([page], limit=2)
        self.assertEqual(len(out), 2)

    def test_listing_failure_does_not_raise(self):
        out, _ = self._crawl(RuntimeError("boom"))
        self.assertEqual(out, [])


class BuildRemoteOkUrlTests(TestCase):
    def test_title_as_search_param(self):
        self.assertEqual(
            build_remoteok_url(" Mobile Developer "),
            "https://remoteok.com/api?search=Mobile+Developer",
        )

    def test_empty_title_returns_none(self):
        self.assertIsNone(build_remoteok_url(""))
        self.assertIsNone(build_remoteok_url(None))
        self.assertIsNone(build_remoteok_url("   "))

    def test_round_trips_through_scraper_for_url(self):
        scraper, source = scraper_for_url(build_remoteok_url("Dev"))
        self.assertIs(scraper, remoteok)
        self.assertEqual(source, "remoteok")


# --- Remote OK (JSON API) ----------------------------------------------------

REMOTEOK_URL = "https://remoteok.com/api?search=backend+engineer"
REMOTEOK_LEGAL = {"last_updated": 1793224395, "legal": "API Terms of Service: ..."}


def _remoteok_job(job_id="1", **overrides):
    """Trimmed shape of a real job object from remoteok.com/api."""
    job = {
        "id": job_id,
        "slug": f"remote-senior-backend-engineer-acme-{job_id}",
        "company": "Acme",
        "position": "Senior Backend Engineer",
        "tags": ["dev", "backend"],
        "description": "<p>Build <strong>APIs</strong>.</p><ul><li>Go</li></ul>",
        "location": "",
        "url": f"https://remoteOK.com/remote-jobs/remote-senior-backend-engineer-acme-{job_id}",
    }
    job.update(overrides)
    return job


class RemoteOkParseJobTests(TestCase):
    def test_maps_fields(self):
        job = _remoteok_job(location="United States")
        out = remoteok.parse_job(job)
        self.assertEqual(out["url"], job["url"])  # ToS: link back to Remote OK
        self.assertEqual(out["title"], "Senior Backend Engineer")
        self.assertEqual(out["company"], "Acme")
        self.assertEqual(out["location"], "United States")
        self.assertIsNone(out["job_type"])
        self.assertEqual(out["remote_option"], RemoteOption.REMOTE)
        self.assertIn("Build\nAPIs", out["description"])
        self.assertNotIn("<", out["description"])

    def test_blank_location_is_none(self):
        self.assertIsNone(remoteok.parse_job(_remoteok_job(location="  "))["location"])

    def test_unescapes_entities(self):
        out = remoteok.parse_job(_remoteok_job(position="Supply &amp; Logistics"))
        self.assertEqual(out["title"], "Supply & Logistics")

    def test_missing_description_returns_none(self):
        self.assertIsNone(remoteok.parse_job(_remoteok_job(description="")))


class RemoteOkCrawlTests(TestCase):
    def _crawl(self, feed, url=REMOTEOK_URL, **kwargs):
        with patch.object(remoteok, "_request_json", side_effect=[feed]) as req:
            out = list(remoteok.crawl(url, client=object(), **kwargs))
        return out, req

    def test_keeps_jobs_matching_every_word(self):
        feed = [
            REMOTEOK_LEGAL,
            _remoteok_job("1"),
            _remoteok_job("2", position="Backend Developer"),
            _remoteok_job("3", position="Staff Engineer, Backend"),
        ]
        out, req = self._crawl(feed)
        self.assertEqual([j["url"][-1] for j in out], ["1", "3"])
        self.assertEqual(req.call_args.args[1], remoteok.FEED_URL)

    def test_skips_duplicate_and_blocked_jobs(self):
        feed = [
            REMOTEOK_LEGAL,
            _remoteok_job("1"),
            _remoteok_job("1"),
            _remoteok_job("2", company="Mindrift"),
            _remoteok_job("3"),
        ]
        out, _ = self._crawl(feed)
        self.assertEqual([j["url"][-1] for j in out], ["1", "3"])

    def test_respects_limit(self):
        feed = [REMOTEOK_LEGAL] + [_remoteok_job(str(i)) for i in range(5)]
        out, _ = self._crawl(feed, limit=2)
        self.assertEqual(len(out), 2)

    def test_fetch_failure_does_not_raise(self):
        out, _ = self._crawl(RuntimeError("boom"))
        self.assertEqual(out, [])

    def test_missing_search_skips_fetch(self):
        out, req = self._crawl([REMOTEOK_LEGAL], url="https://remoteok.com/api")
        self.assertEqual(out, [])
        req.assert_not_called()


class JobBriefSerializerExpiryTests(TestCase):
    def test_is_expired(self):
        from api.v1.serializers import JobBriefSerializer

        def make(url, expires_at):
            return Job.objects.create(
                url=url, title="t", description="d", expires_at=expires_at
            )

        past = make("https://himalayas.app/a", timezone.now() - timedelta(hours=1))
        future = make("https://himalayas.app/b", timezone.now() + timedelta(days=1))
        none = make("https://himalayas.app/c", None)
        self.assertTrue(JobBriefSerializer(past).data["is_expired"])
        self.assertFalse(JobBriefSerializer(future).data["is_expired"])
        self.assertFalse(JobBriefSerializer(none).data["is_expired"])


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


# --- Workable (search JSON API) ---------------------------------------------

WK_URL = "https://jobs.workable.com/search?query=Backend+Engineer&location=Indonesia"


def _wk_job(jid, title="Backend Engineer", days_ago=1, **overrides):
    """Trimmed shape of a real job from jobs.workable.com/api/v1/jobs."""
    created = timezone.now() - timedelta(days=days_ago)
    job = {
        "id": jid,
        "title": title,
        "description": "<p>Build <b>things</b>.</p>",
        "requirementsSection": "<ul><li>Python</li></ul>",
        "benefitsSection": "",
        "employmentType": "Full-time",
        "workplace": "hybrid",
        "url": f"https://jobs.workable.com/view/{jid}/backend-engineer",
        "location": {
            "city": "Jakarta",
            "subregion": "Jakarta",
            "countryName": "Indonesia",
        },
        "created": created.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "company": {"title": "Acme"},
    }
    job.update(overrides)
    return job


class WorkableParseJobTests(TestCase):
    def test_maps_fields(self):
        out = workable.parse_job(
            _wk_job("A", workplace="remote", employmentType="Contract")
        )
        self.assertEqual(
            out["url"], "https://jobs.workable.com/view/A/backend-engineer"
        )
        self.assertEqual(out["company"], "Acme")
        self.assertEqual(out["location"], "Jakarta, Indonesia")
        self.assertEqual(out["job_type"], JobType.CONTRACT)
        self.assertEqual(out["remote_option"], RemoteOption.REMOTE)
        self.assertEqual(out["description"], "Build\nthings\n.\nPython")

    def test_unknown_values_are_none(self):
        out = workable.parse_job(_wk_job("A", workplace="", employmentType="Other"))
        self.assertIsNone(out["job_type"])
        self.assertIsNone(out["remote_option"])

    def test_missing_description_returns_none(self):
        job = _wk_job("A", description="", requirementsSection="")
        self.assertIsNone(workable.parse_job(job))


class WorkableCrawlTests(TestCase):
    def _crawl(self, pages, url=WK_URL, **kwargs):
        with patch.object(workable, "_request_json", side_effect=pages) as req:
            out = list(workable.crawl(url, client=object(), sleep=0, **kwargs))
        return [p["url"].split("/")[4] for p in out], req

    def test_filters_and_paginates(self):
        page1 = {
            "jobs": [
                _wk_job("A", "Senior Backend Engineer"),
                _wk_job("A", "Senior Backend Engineer"),  # duplicate
                _wk_job("B", "Business Development"),  # fuzzy hit, wrong words
                _wk_job("C", "Backend Engineer", days_ago=200),  # stale
                _wk_job("D", "Backend Engineer", company={"title": "Mindrift"}),
            ],
            "nextPageToken": "tok1",
        }
        page2 = {"jobs": [_wk_job("E", "Backend Engineer II")], "nextPageToken": None}
        ids, req = self._crawl([page1, page2])
        self.assertEqual(ids, ["A", "E"])
        first, second = (c.args[1] for c in req.call_args_list)
        self.assertIn("query=Backend+Engineer&location=Indonesia", first)
        self.assertNotIn("pageToken", first)
        self.assertIn("pageToken=tok1", second)

    def test_always_searches_indonesia(self):
        _, req = self._crawl(
            [{"jobs": []}], url="https://jobs.workable.com/search?query=Dev"
        )
        self.assertIn("location=Indonesia", req.call_args.args[1])

    def test_limit_and_max_pages(self):
        page = {"jobs": [_wk_job("A"), _wk_job("B")], "nextPageToken": "t"}
        ids, _ = self._crawl([page], limit=1)
        self.assertEqual(ids, ["A"])
        _, req = self._crawl([page, page, page], max_pages=2)
        self.assertEqual(req.call_count, 2)

    def test_fetch_error_logs_and_stops(self):
        with self.assertLogs("jobs.scrapers.workable", level="ERROR"):
            ids, _ = self._crawl(RuntimeError("boom"))
        self.assertEqual(ids, [])

    def test_no_query_warns(self):
        with self.assertLogs("jobs.scrapers.workable", level="WARNING"):
            ids, req = self._crawl([], url="https://jobs.workable.com/search")
        self.assertEqual(ids, [])
        req.assert_not_called()


class WorkableUrlTests(TestCase):
    def test_build_url_always_indonesia(self):
        self.assertEqual(
            build_workable_url("Mobile Developer"),
            "https://jobs.workable.com/search?query=Mobile+Developer&location=Indonesia",
        )
        self.assertIsNone(build_workable_url("  "))

    def test_round_trips_through_scraper_for_url(self):
        scraper, source = scraper_for_url(build_workable_url("Dev"))
        self.assertIs(scraper, workable)
        self.assertEqual(source, "workable")


# --- Skill Map ---------------------------------------------------------------

from django.core.cache import cache  # noqa: E402
from django.test import override_settings  # noqa: E402

from billing.models import Plan  # noqa: E402
from jobs.models import SkillMapPage, SkillMapSnapshot  # noqa: E402
from jobs.scrapers.filters import title_has_words, title_words  # noqa: E402
from jobs.skill_map.services import (  # noqa: E402
    compute_snapshot,
    format_date_id,
    refresh_page,
    skill_key,
    title_matches,
    visible_pages,
)


def _job(n, title, hard=(), soft=(), company=None, **kw):
    return Job.objects.create(
        url=f"https://example.com/job/{n}",
        title=title,
        company=company or f"Company {n}",
        description="x",
        hard_skills=list(hard),
        soft_skills=list(soft),
        **kw,
    )


class TitleWordsTests(TestCase):
    def test_splits_lowercases_and_drops_single_letters(self):
        self.assertEqual(title_words("UI/UX Designer"), ["ui", "ux", "designer"])
        self.assertEqual(title_words("C Developer"), ["developer"])
        self.assertEqual(title_words(None), [])

    def test_title_has_words_tolerates_plural_and_al(self):
        hits = [
            ("Operations Intern (E-Commerce Logistic)", ["logistic", "operational"]),
            ("Logistics Manager", ["logistics"]),
            ("Senior Data Analysts", ["data", "analyst"]),
        ]
        misses = [
            ("Business Development", ["developer"]),
            ("Warehouse & Logistic Officer", ["logistic", "operational"]),
            ("Portfolio Manager", ["ios"]),
        ]
        for title, words in hits:
            self.assertTrue(title_has_words(title, words), title)
        for title, words in misses:
            self.assertFalse(title_has_words(title, words), title)

    def test_title_matches_word_starts_and_exclusions(self):
        self.assertTrue(title_matches("Senior Data Analysts", ["data", "analyst"], []))
        self.assertFalse(title_matches("Build Engineer", ["ui"], []))
        self.assertFalse(
            title_matches("Data Analyst Intern", ["data", "analyst"], ["intern"])
        )


class SkillKeyTests(TestCase):
    def test_casefold_whitespace_and_aliases(self):
        self.assertEqual(skill_key("  Python "), "python")
        self.assertEqual(skill_key("MS  Excel"), "excel")
        self.assertEqual(skill_key("Microsoft Excel"), "excel")
        self.assertEqual(skill_key("ReactJS"), "react")

    def test_format_date_id(self):
        from datetime import date

        self.assertEqual(format_date_id(date(2026, 8, 1)), "1 Agu 2026")


class ComputeSnapshotTests(TestCase):
    def setUp(self):
        self.page = SkillMapPage.objects.create(
            slug="data-analyst", title="Data Analyst"
        )
        _job(
            1,
            "Data Analyst",
            ["SQL", "Excel"],
            ["Communication"],
            remote_option="remote",
        )
        _job(
            2,
            "Senior Data Analyst",
            ["sql", "MS Excel", "Python"],
            job_type="full-time",
        )
        _job(3, "Data Analyst Intern", ["SQL"])
        _job(4, "Data Engineer", ["Spark"])  # title mismatch
        _job(5, "Data Analyst", [])  # no skills yet
        # The same posting as job 1, arriving from a second board.
        _job(
            6,
            "Data Analyst",
            ["SQL", "Excel"],
            ["Communication"],
            company="Company 1",
            remote_option="remote",
        )
        old = _job(7, "Data Analyst", ["COBOL"])
        Job.objects.filter(pk=old.pk).update(
            created_on=timezone.now() - timedelta(days=200)
        )

    def test_counts_each_skill_once_per_matching_job(self):
        data = compute_snapshot(self.page)
        self.assertEqual(data["job_count"], 3)
        hard = {s["name"]: (s["count"], s["pct"]) for s in data["hard_skills"]}
        self.assertEqual(hard["SQL"], (3, 100))
        # "Excel" and "MS Excel" merge; one spelling is shown.
        excel = [s for s in data["hard_skills"] if skill_key(s["name"]) == "excel"]
        self.assertEqual(len(excel), 1)
        self.assertEqual(excel[0]["count"], 2)
        self.assertEqual(hard["Python"], (1, 33))
        self.assertNotIn("Spark", hard)
        self.assertNotIn("COBOL", hard)
        self.assertEqual(data["soft_skills"][0]["name"], "Communication")
        self.assertEqual(
            [(r["value"], r["pct"]) for r in data["remote_options"]], [("remote", 33)]
        )
        self.assertEqual([t["value"] for t in data["job_types"]], ["full-time"])

    def test_exclude_words_and_match_words(self):
        self.page.exclude_words = "intern"
        self.assertEqual(compute_snapshot(self.page)["job_count"], 2)
        self.page.match_words = "data"
        self.page.exclude_words = ""
        self.assertEqual(compute_snapshot(self.page)["job_count"], 4)

    def test_refresh_page_overwrites_same_day(self):
        refresh_page(self.page)
        refresh_page(self.page)
        self.assertEqual(SkillMapSnapshot.objects.filter(page=self.page).count(), 1)
        self.assertEqual(self.page.latest_snapshot().job_count, 3)


@override_settings(FRONTEND_URL="https://cariinkerja.id")
class SkillMapViewTests(TestCase):
    def setUp(self):
        cache.clear()
        Plan.objects.create(name="1 Pencarian", price=49000, duration_days=30)
        for i in range(3):
            _job(
                i, "Backend Engineer", ["Go", "PostgreSQL"], company=f"Rahasia Corp {i}"
            )
        self.page = SkillMapPage.objects.create(
            slug="backend-engineer",
            title="Backend Engineer",
            is_published=True,
            min_jobs=3,
        )
        self.thin = SkillMapPage.objects.create(
            slug="ios-engineer", title="iOS Engineer", is_published=True, min_jobs=3
        )
        self.draft = SkillMapPage.objects.create(
            slug="draft", title="Backend Engineer", is_published=False, min_jobs=1
        )
        for p in (self.page, self.thin, self.draft):
            refresh_page(p)

    def test_detail_renders_aggregates_without_company_names(self):
        resp = self.client.get("/skill/backend-engineer/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Skill yang paling dicari buat", html)
        self.assertIn("PostgreSQL", html)
        self.assertIn("100%", html)
        self.assertIn("3 loker", html)
        self.assertIn("Rp 49.000 / 30 hari", html)
        self.assertIn(
            '<link rel="canonical" href="https://cariinkerja.id/skill/backend-engineer/"',
            html,
        )
        self.assertIn("/login?ref=skillmap-backend-engineer", html)
        self.assertNotIn("Rahasia Corp", html)
        self.assertNotIn("JobPosting", html)
        self.assertNotIn("gratis", html.lower())

    def test_thin_unpublished_and_unknown_pages_404(self):
        self.assertEqual(self.client.get("/skill/ios-engineer/").status_code, 404)
        self.assertEqual(self.client.get("/skill/draft/").status_code, 404)
        self.assertEqual(self.client.get("/skill/nope/").status_code, 404)

    def test_index_and_sitemap_list_only_visible_pages(self):
        self.assertEqual([p.slug for p, _ in visible_pages()], ["backend-engineer"])
        index = self.client.get("/skill/").content.decode()
        self.assertIn("/skill/backend-engineer/", index)
        self.assertNotIn("/skill/ios-engineer/", index)
        resp = self.client.get("/skill/sitemap.xml")
        self.assertEqual(resp["Content-Type"], "application/xml")
        xml = resp.content.decode()
        self.assertIn("<loc>https://cariinkerja.id/skill/backend-engineer/</loc>", xml)
        self.assertNotIn("ios-engineer", xml)
        self.assertNotIn("/skill/draft/", xml)

    def test_refresh_task_snapshots_every_page(self):
        from jobs.tasks import refresh_skill_maps

        result = refresh_skill_maps()
        self.assertEqual(result["backend-engineer"], 3)
        self.assertEqual(result["ios-engineer"], 0)


class SkillMapCommandTests(TestCase):
    def test_candidates_lists_preference_titles_with_job_counts(self):
        from profiles.models import Preference, Profile

        profile = Profile.objects.create()
        for _ in range(2):
            Preference.objects.create(profile=profile, title="Backend Engineer")
        Preference.objects.create(profile=profile, title="backend  engineer")
        _job(1, "Backend Engineer", ["Go"])
        out = io.StringIO()
        call_command("skill_map_candidates", "--min-jobs", "1", stdout=out)
        line = next(
            ln for ln in out.getvalue().splitlines() if "[backend-engineer]" in ln
        )
        self.assertEqual(line.split()[:3], ["3", "1", "✓"])

    def test_create_makes_live_pages_only_for_titles_with_enough_jobs(self):
        from profiles.models import Preference, Profile

        profile = Profile.objects.create()
        Preference.objects.create(profile=profile, title="data analyst")
        Preference.objects.create(profile=profile, title="Data Analyst")
        Preference.objects.create(profile=profile, title="iOS Engineer")
        for i in range(2):
            _job(i, "Data Analyst", ["SQL"])
        SkillMapPage.objects.create(slug="ios-engineer", title="iOS Engineer")

        out = io.StringIO()
        args = ("skill_map_candidates", "--create", "--min-jobs", "2")
        call_command(*args, stdout=out)

        page = SkillMapPage.objects.get(slug="data-analyst")
        self.assertEqual(page.title, "Data Analyst")
        self.assertTrue(page.is_published)
        self.assertEqual(page.min_jobs, 2)
        self.assertEqual(page.latest_snapshot().job_count, 2)
        self.assertEqual(SkillMapPage.objects.count(), 2)  # existing one untouched
        self.assertIn("created 1 page(s)", out.getvalue())

        # Running again creates nothing new.
        call_command(*args, stdout=io.StringIO())
        self.assertEqual(SkillMapPage.objects.count(), 2)

    def test_create_draft_leaves_pages_unpublished(self):
        from profiles.models import Preference, Profile

        Preference.objects.create(profile=Profile.objects.create(), title="Backend")
        _job(1, "Backend", ["Go"])
        call_command(
            "skill_map_candidates",
            "--create",
            "--draft",
            "--min-jobs",
            "1",
            stdout=io.StringIO(),
        )
        self.assertFalse(SkillMapPage.objects.get(slug="backend").is_published)

    def test_backfill_filters_and_dry_run(self):
        _job(1, "A", source="workable")
        _job(2, "B", source="indeed")
        old = _job(3, "C", source="workable")
        Job.objects.filter(pk=old.pk).update(
            created_on=timezone.now() - timedelta(days=200)
        )
        out = io.StringIO()
        call_command(
            "backfill_job_skills",
            "--source",
            "workable",
            "--since-days",
            "90",
            "--dry-run",
            stdout=out,
        )
        self.assertIn("1 job(s) would be queued", out.getvalue())
