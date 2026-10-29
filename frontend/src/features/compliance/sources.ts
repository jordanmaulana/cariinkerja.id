// Mirror of _docs/job_sources.json (name + permission_urls) — the frontend
// Docker build only sees frontend/, so update both together.

export type SourcePermission = { url: string; statement: string };
export type JobSource = { name: string; permissions: SourcePermission[] };

export const JOB_SOURCES: JobSource[] = [
  {
    name: "Himalayas",
    permissions: [
      {
        url: "https://himalayas.app/terms",
        statement:
          'Clause 113: API may be used "in personal and commercial integrations"; apply via applicationLink, link back, no passing jobs to Google Jobs/LinkedIn/aggregators (incl. JobPosting schema).',
      },
      {
        url: "https://himalayas.app/api",
        statement: "Public API docs; free key gives 60 req/min, 10,000/day.",
      },
    ],
  },
  {
    name: "Jobicy",
    permissions: [
      {
        url: "https://jobicy.com/jobs-rss-feed",
        statement:
          'Free API "can be used in commercial projects"; may "store, cache, process, and redistribute". "Clearly credit Jobicy as the original source" with a direct link; apply links go to the original job page on Jobicy; start an automated sync pass "no more than once per hour".',
      },
    ],
  },
  {
    name: "Workable",
    permissions: [
      {
        url: "https://help.workable.com/hc/en-us/articles/4420464031767-Utilizing-the-XML-Job-Feed",
        statement:
          'Public XML feed of all customers\' published jobs; offered for "a job board/partner we don\'t integrate with". Keep job URLs unchanged. No formal licence text.',
      },
    ],
  },
  {
    name: "Remote OK",
    permissions: [
      {
        url: "https://remoteok.com/api",
        statement:
          '"legal" field in API response: link back (follow, no nofollow) and mention Remote OK as source; no logo without written permission.',
      },
    ],
  },
  {
    name: "Remotive",
    permissions: [
      {
        url: "https://remotive.com/remote-jobs/api",
        statement:
          "Link back to Remotive URL and mention Remotive as source; do not submit jobs to third-party sites (Jooble, Neuvoo, Google Jobs, LinkedIn Jobs).",
      },
      {
        url: "https://github.com/remotive-com/remote-jobs-api",
        statement:
          "README: 24h delay, max ~4 fetches/day, >2 req/min blocked, no using jobs to collect emails/signups.",
      },
    ],
  },
];
