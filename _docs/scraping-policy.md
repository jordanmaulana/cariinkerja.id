# Scraping policy & source register

How cariinkerja.id decides what it is willing to crawl, and what it actually
crawls today. This is a factual register plus our own rules — **not a legal
opinion**. Where something is legally grey it says so.

Last full verification: **2026-09-09**. Re-verify before adding a source, and
whenever a source starts failing in an unfamiliar way.

---

## 1. Source register

Every row was checked by fetching the live `robots.txt` and, where reachable,
the terms page. "WAF" is the response to a plain HTTP GET with no browser
impersonation.

### Sources we crawl

| Source | robots.txt on the paths we use | ToS on automated access | WAF | Verdict |
|---|---|---|---|---|
| **Kalibrr** | Allowed. Whole file is `Disallow: /root` + `Disallow: /candidate/profile` | Anti-scraping clause found is scoped to *Kalibrr Free account holders*, not anonymous crawlers | none | **Clean** |
| **Kitalulus** | Allowed. `Disallow: /auth/`, `/my/` only | No anti-scraping clause found in the S&K (searched `scrap`/`robot`/`crawl`/`otomatis`/`mengekstrak`) | none | **Clean** |
| **Karirhub** (Kemnaker) | Allowed. File has **zero directives** — all comments. We read its public JSON API on `api.kemnaker.go.id`, which serves no robots.txt at all (404) — everything permitted by default under RFC 9309 | No terms page located | none | **Clean** |
| **Dealls** | Allowed. `User-agent: *` / `Allow: /` | Bars *redistributing* content without written consent. Does not prohibit crawling | none | **OK, worth a partnership email** |
| **Indeed** | **Disallowed.** `/jobs/ID/`, `/job/`, `/viewjob?`, `/*&start=` — the exact paths we crawl | Automation clause found is scoped to applying; general clause unverified | **403 challenge** | **Deviation — see §3** |
| **JobStreet** (SEEK) | **Disallowed.** `*/job/` and `*?` (kills every query URL) | §7(d) bans "data mining, robots, screen scraping … for reproducing information contained on our websites … on your own website" | **403 challenge** | **Deviation — see §3** |
| **LinkedIn** | **Disallowed.** No `User-agent: *` group exists; file header reads "The use of robots or other automated means to access LinkedIn without the express permission of LinkedIn is strictly prohibited" | User Agreement §8.2 bans scraping *and* circumventing access controls | authwall / HTTP 999 | **Deviation — see §3** |

### Checked and rejected

| Source | Why not |
|---|---|
| **Glints** | robots.txt permits job detail pages, but the WAF 403s everything — including the sitemap its own robots.txt advertises. Their error page says "access is currently restricted due to automated traffic". High relevance to our segment; the blocker is commercial, so this is a conversation to have, not a crawler to write. |
| **Tech in Asia Jobs** | robots.txt is unusually welcoming (an explicit `User-agent: ClaudeBot` allow group) and it publishes a 174-file jobs sitemap, but job pages are **client-side rendered** — no JSON-LD, no description in the HTML. Needs a headless browser we do not have. Revisit if browser infra ever lands. |
| **Karir.com** | Permissive robots with an explicit `Crawl-delay: 1`, and no CDN in front of the origin. Viable, but client-rendered and mid-volume. Reasonable next addition. |
| **Loker.id** | robots.txt is `Disallow:` (allow all) but the WAF serves a 403 JS challenge. Low-value source, would require evasion. No. |
| **Urbanhire** | Dead — Cloudflare error 1016, no origin. |
| **TopKarir** | Origin refusing TLS connections from two networks. |
| **Startup Jobs Asia** | Timeouts; likely defunct. |
| **Jobs.id** | Redirects to Karir.com. Not a separate source. |
| **JobsDB** | Redirects to JobStreet. Same entity, same terms. |
| **Ekrut** | Jobs page is ~7KB — the board is effectively empty. |

### Not yet built, worth doing

- **ATS public job-board APIs** — Greenhouse, Lever, Ashby, Workable, Recruitee, Personio. Documented, unauthenticated, and the *employer* owns the content, so this is the cleanest lane available. The catch is discovery: you need each employer's board token, and Indonesian penetration is thin (venture-backed tech and multinationals). Quality, not coverage.
- **Licensed aggregator APIs** — Jooble and Careerjet both cover Indonesia and both hand out free keys. Permissioned, and would solve the volume problem the ATS lane cannot.
- **schema.org `JobPosting` JSON-LD from company career pages** — the publisher emits it *for* machine consumption. Defensible and scalable. Note it does **not** override a robots.txt `Disallow` on the page carrying it.

---

## 2. Rules we hold ourselves to

1. **Honor robots.txt.** It is the operator's explicit, machine-readable statement of consent. It is not binding law almost anywhere, but ignoring a `Disallow` is the single fact most likely to turn a civil dispute into a bad-faith narrative — and see §4 on why that matters more in Indonesia than in the US.
2. **Never evade anti-bot measures.** No CAPTCHA solving, no TLS/JA3 fingerprint spoofing, no residential proxy rotation to defeat an IP ban, no stealth-patched headless browsers. If a site is blocking you, that is the answer. This is the brightest line in this document.
3. **Identify the crawler.** New scrapers send `CariinKerjaBot/1.0 (+https://cariinkerja.id)` (`jobs/consts.py:BOT_USER_AGENT`) and no browser impersonation. Kalibrr, Kitalulus and Karirhub all serve full content to it — verified 2026-09-09. A site that can cheaply block us and chooses not to has tacitly tolerated us; that only works if blocking us is actually cheap for them.
4. **Rate-limit conservatively.** Per-request `sleep` of 1.5–2.5s plus jitter, `CRAWL_ITEM_LIMIT = 10` per URL, once-daily schedule. Prefer designs that need fewer requests: the Kalibrr scraper is single-phase and fetches a whole crawl in **one** request. Karirhub reads the same public JSON API its own site calls (`jobs/scrapers/karirhub.py:LIST_API`) rather than the rendered pages — cheaper for them than serving Next.js documents, and it returns complete descriptions where the page's RSC payload left ~20% of them as unresolved `$NN` chunk pointers.
5. **Link back, don't republish.** We store facts and score them; the user is sent to the original posting. This also keeps us structurally unlike a meta-search mirror — see §4.
6. **Don't collect personal data.** Strip recruiter names, emails and phone/WhatsApp numbers **at ingest**, not at display. Keep the organisation, drop the human. Existing precedents in code: `jobs/scrapers/dealls.py` ignores `author`; `jobs/scrapers/kalibrr.py` ignores `es_recruiter_last_seen`; `jobs/scrapers/karirhub.py` reads only `employer.name` and drops it entirely when the vacancy is flagged `confidential`.
7. **Honor takedowns fast.** See §5 — we do not yet have a published route for this.

---

## 3. Known deviations

**Indeed, JobStreet and LinkedIn are crawled against an explicit `Disallow`,
and the Indeed scraper deliberately evades a Cloudflare challenge.**

`jobs/scrapers/indeed.py` rotates three TLS fingerprints (`IMPERSONATE_TARGETS`),
performs a homepage warm-up to seed Cloudflare clearance cookies, and keeps its
User-Agent consistent with the spoofed fingerprint *specifically so the
mismatch does not read as a bot signal*. That is rule 2 above, broken on
purpose.

**Why it is still running:** these three are the highest-volume sources and
dropping them today would gut coverage. The decision on 2026-09-09 was to add
defensible sources first, measure how much coverage they actually replace, and
then revisit each incumbent — not to break the product in one step.

**Exit condition:** once the clean sources plus a licensed aggregator API cover
enough of the market, retire the incumbents in risk order — LinkedIn first
(they sued Proxycurl, a ~$10M-ARR company, into shutdown in July 2025), then
Indeed, then JobStreet. SEEK is the one most likely to send a letter: its ToS
clause describes this product category almost exactly, and some SEEK terms are
governed by Indonesian law, so a contract claim could be brought here.

This section exists so the exposure is a priced business decision rather than
an accident. It was previously recorded nowhere.

---

## 4. Legal context

Factual summary, not advice. Get Indonesian counsel before betting the company
on any of it.

**The US case law is mostly reassuring on hacking statutes and unhelpful on
contract.** *Van Buren* (2021) narrowed CFAA "exceeds authorized access" to a
gates-up-or-down test, so violating a ToS is not itself a US federal crime.
*hiQ v. LinkedIn* (9th Cir. 2022) held scraping public pages likely does not
violate the CFAA — but hiQ then **lost on breach of contract**, and settled in
December 2022 for $500,000 plus a permanent injunction and destruction of all
LinkedIn-derived data. *Meta v. Bright Data* (N.D. Cal. 2024) is the most
useful case for us: scraping while **logged out** meant Bright Data was never a
"user" bound by the terms. The practical rule that follows is *never create an
account, never log in, never click through* — which is how all seven of our
scrapers already work.

**Indonesian law diverges, and it diverges against us.**

- **UU ITE Pasal 30** criminalises accessing another's electronic system "tanpa
  hak" (without right). Indonesia has **no *Van Buren*** narrowing that phrase,
  so the argument that a ToS violation makes access unlawful is colorable and
  untested here. **Pasal 30(3)** — access by breaching or bypassing a security
  system — is where anti-bot evasion lands, and it carries the heaviest penalty
  tier. This is the specific reason rule 2 is the brightest line in §2.
- **UU 27/2022 (PDP)** has **no publicly-available-data carve-out**. Art. 2 is
  extraterritorial; Art. 15 exemptions are narrow and closed. Sanctions reach 2%
  of annual revenue, plus criminal liability for unlawful collection. It has
  been fully enforceable since **2024-10-17** even though the supervisory body
  (Lembaga PDP) still does not exist — the absence of a regulator removes the
  *guidance*, not the *liability*. The "legitimate interest" basis in Art. 20
  exists but is completely untested; anyone confident that job aggregation
  qualifies is guessing. **This is why rule 6 is the highest-leverage control
  we have.**
- **UU 28/2014 (Hak Cipta) Pasal 40(1)** expressly protects *kompilasi data*.
  A job board's compiled listings are plausibly a protected work in Indonesian
  law — so the US "facts aren't copyrightable" intuition does not transfer.
  Individual facts stay unprotected; **the compilation is the exposure.** Bulk
  mirroring of one board's inventory is riskier here than it looks from US law.

**One structural point worth protecting deliberately.** In *Innoweb v. Wegener*
(CJEU C-202/12) a dedicated meta-search engine over classified ads was held to
infringe by re-utilisation — even though it stored nothing — because it
reproduced the target's search functionality and result presentation. Our
product scores postings against a specific candidate profile and links out. It
is not a mirror of anyone's search UI. **Do not drift toward full-text
redisplay or a clone of a source's search UX**; that difference is doing real
work.

---

## 5. Checklist for adding a source

1. Fetch `https://<host>/robots.txt`. Quote the lines covering the listing and
   detail paths. If they disallow those paths, stop and escalate — do not just
   proceed.
2. Read the terms page. Search for `scrap`, `robot`, `crawl`, `automated`,
   `otomatis`, `mengekstrak`. Quote what you find, or record that you looked
   and found nothing.
3. Test with `BOT_USER_AGENT`. If the honest UA gets full content, use plain
   `httpx` and no impersonation. If it is challenged, that is a signal to stop,
   not a problem to route around.
4. Prefer a documented API, then structured data the publisher emits for
   machines (JSON-LD, RSC props, sitemaps), then HTML parsing. In that order.
5. Check what personal data the payload carries and drop it in the parser, not
   downstream.
6. **Add a row to §1 with the date before writing the scraper.**

---

## 6. Open items

- **No robots.txt parsing anywhere in the codebase.** `grep robotparser` returns
  nothing. Compliance is currently a human check recorded in this file, not an
  enforced runtime behaviour. The four legacy scrapers (Indeed, JobStreet,
  LinkedIn, Dealls) still send browser User-Agents and honor no `Crawl-delay`.
  Worth building when the incumbent phase-out starts.
- **No published takedown route.** Rule 7 is a stated intent, not a working
  process. A `/bot` page explaining what the crawler does plus a named contact
  and a persistent suppression list is cheap insurance and the strongest
  available evidence of good faith. `BOT_USER_AGENT` currently points at the
  site root because that page does not exist yet.
- **No per-host rate limiting.** Concurrency is whatever Celery gives it — N
  workers can hit the same host simultaneously with no coordination.
- **UU PDP "legitimate interest" is untested.** Worth an Indonesian firm's
  opinion before scaling.
