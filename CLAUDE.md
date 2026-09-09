# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Django 5.2, Python ≥3.10, DRF (`rest_framework` + `rest_framework.authtoken`). DRF defaults: `TokenAuthentication` + `IsAuthenticated` (`core/settings.py`).
- **Database**: Postgres in Docker / prod (`psycopg`); SQLite fallback for host dev. Selection is implicit in `core/settings.py` — if `POSTGRES_HOST` is set in env it uses Postgres, otherwise it falls back to `db.sqlite3` tuned with `journal_mode=WAL`, `synchronous=NORMAL`, `transaction_mode=IMMEDIATE`, `timeout=30`. Don't assume the dev DB is the prod DB.
- Dep mgmt via `uv` (`pyproject.toml`, `uv.lock`); lint/format via `ruff`. Frontend uses `pnpm`.
- Static: Whitenoise with `CompressedManifestStaticFilesStorage`; Tailwind v4 (`static/input.css` → `static/output.css`).
- Frontend SPA under `frontend/`: Vite + React 19 + TS, **TanStack Router** (file-based, generated `routeTree.gen.ts`) + **TanStack Query**, **Jotai** for state, **shadcn / Radix** + Tailwind v4 for UI, `recharts` for charts, `react-toastify` for toasts. Talks to Django via `/api/v1/`.
- Celery + Redis for async work; `django_celery_beat` (`DatabaseScheduler`) for periodic tasks — schedules edited via Django admin, not code. `CELERY_TASK_ACKS_LATE=True`, `CELERY_TASK_REJECT_ON_WORKER_LOST=True`.
- LLM: `openai` SDK, structured output via `pydantic` (`SkillAssessment`, `RelevanceCheck`, `JobSkills`, `LinkedInIngest`). Model from `OPENAI_MODEL` (settings default `gpt-4o-mini`). Cheap calls (relevance gate, job-skill extraction) read `OPENAI_RELEVANCE_MODEL` via `getattr(settings, ..., "gpt-4o-mini")` — that setting is **not** declared in `core/settings.py`, so it's `gpt-4o-mini` unless you add it. All OpenAI calls go through `core.openai.get_prompt_manager()`.
- Scrapers use `curl-cffi` (TLS fingerprint impersonation) + `lxml`/`beautifulsoup4`.
- LinkedIn *profile* ingestion uses **Apify** (`apify-client`, actor `harvestapi/linkedin-profile-scraper`) — distinct from the LinkedIn *jobs* scraper in `jobs/scrapers/linkedin.py`, which is our own.
- Auth: `core.auth.EmailBackend` (login by email) **plus** Google OAuth via `/api/v1/auth/google/` (verifies `GOOGLE_OAUTH_CLIENT_ID`).
- Payments: Mayar (`core/payments/mayar.py`) — payment-link create + webhook verified by `X-Callback-Token`.
- Realtime: Redis pub/sub (`core/realtime.py`) → SSE endpoint `/api/v1/subscriptions/stream/` (EventSource auth via `?token=` query param, since EventSource cannot set headers).
- Notifications:
  - Discord webhook (`core/notifications/discord.py`), called from Celery tasks; no-ops when `DISCORD_WEBHOOK_URL` is empty.
  - Transactional email (`core/notifications/email.py:send_email`) using Django's SMTP backend; no-ops with a warning when `EMAIL_HOST` / `EMAIL_HOST_USER` are unset. Daily summary task is `assessment.tasks.email_morning_high_score_summary` (registered via beat); links into the SPA use `FRONTEND_URL`. Superuser admin page at `/settings/smtp-test/` (`SmtpTestView`) displays the live SMTP config and sends a test message.
- `TIME_ZONE = "Asia/Jakarta"` for both Django and Celery (`USE_TZ=True`).

## Common commands

All via `Makefile` (uses `uv run`):

```sh
make dev        # runserver on :8000
make mmg        # makemigrations
make migrate    # migrate
make lint       # ruff format + ruff check --fix
make upgrade    # uv sync + uv lock --upgrade
make tw-run     # tailwind watch
make tw-build   # tailwind one-shot build
make web        # cd frontend && pnpm run dev
make worker     # celery worker (sets OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES for macOS fork safety)
make beat       # celery beat (DatabaseScheduler)
make audit      # cd frontend && pnpm audit fix
make dock       # docker compose down/build/up -d --env-file .env.docker (then tails logs)
make shell      # bash into the running compose backend container
```

There is **no `make test`** — run Django's test runner directly.

Tests: `uv run manage.py test` (full suite, ~194 tests), `uv run manage.py test <app>` (one app), or `uv run manage.py test <app>.tests.<TestClass>.<test_method>` for a single test (e.g. `uv run manage.py test jobs.tests.JobModelTests.test_create`). Scraper tests parse checked-in HTML from `jobs/fixtures_html/` — no network.

Frontend-only (no Make target): `cd frontend && pnpm run lint` (eslint), `cd frontend && pnpm run build` (`tsc -b && vite build`).

`update.sh` is the prod deploy script: `git pull` → `docker compose build` → `up -d` → wait for postgres healthy → `manage.py migrate`. The Docker image runs `docker/backend-entrypoint.sh`, which waits for Postgres then branches on `ROLE` env (`web` runs `migrate` + `collectstatic` before exec'ing CMD; `worker` and `beat` skip those). Compose services: `postgres`, `redis`, `backend`, `worker`, `beat`, `frontend`.

### Management commands

Ad-hoc one-shot crawls (recurring crawls run through the Celery pipeline below). All four take the same flags and upsert `Job` rows by `url` inside `transaction.atomic`:

```sh
uv run manage.py crawl_indeed    "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
uv run manage.py crawl_jobstreet "<listing-url>" [...]
uv run manage.py crawl_linkedin  "<listing-url>" [...]
uv run manage.py crawl_dealls    "<listing-url>" [...]
```

Defaults: `--max-pages 1`, `--limit 20`, `--sleep` from each scraper's `DEFAULT_SLEEP` (Indeed/LinkedIn 2.5s, JobStreet/Dealls 1.5s).

Other commands: `backfill_job_skills`, `backfill_jobstreet_urls --dry-run`.

**Gotcha:** two apps define `crawl_linkedin` — `jobs/` (listing-URL job crawler) and `profiles/` (Apify *profile* ingest, takes a `profile_id`). Django resolves the name to **`jobs`** (earlier in `INSTALLED_APPS` wins), so the profiles one is unreachable via `manage.py`; call `profiles.methods.crawl_and_ingest_linkedin` or the `crawl_linkedin_for_profile` task instead. Rename one if you touch this area.

## Architecture

Django project rooted at `core/` with four domain apps: `profiles`, `jobs`, `assessment`, `billing`. `core` is also installed as an app (holds `BaseModel` + `AppSetting`, the server-rendered admin dashboard, the Mayar payments adapter, Redis realtime, Discord/email notifications, dashboard cache, and subscription polling tasks). The DRF surface lives in a **top-level `api/` package**, not under `core/`. The `billing` app owns `Plan`, `Subscription`, `SubscriptionStatus`, `effective_price` (Open-to-Work discount) and `upgrades.py` (proration).

### Shared base — `core/models.py`

- `BaseModel` (abstract): primary key is a stringified BSON `ObjectId` (`make_object_id`), plus `created_on`, `updated_on`, optional `actor` FK to `auth.User`. Default ordering by `id`, index on `created_on`. **All new domain models should inherit from `BaseModel`** unless intentionally diverging (note: `jobs.Job` does NOT inherit — it duplicates the id/timestamp fields manually; treat as legacy and prefer `BaseModel` for new work).
- `AppSetting`: typed key/value store with `AppSetting.get(key, value_type, default)` for runtime config (`value_type` ∈ `str|int|float|bool`).

### Domain model shape

- `profiles.Profile` — candidate identity. Optional `OneToOne` to `auth.User`. Stores `linkedin_url`, `linkedin_raw` (Apify paste), `full_profile` (LLM-cleaned, fed to assessor), `open_to_work` (drives `linkedin_discount_eligible` → discount on the cheapest active plan, see `billing.effective_price`), `linkedin_quality_ok`/`linkedin_quality_reason`, `suggested_full_name`, and a `whitelist` flag that bypasses plan limits **and the subscription crawl gate**.
- `profiles.Preference` — candidate's job preference (FK `Profile`). `title`; `job_type` and `remote_option` are **JSON lists** of `jobs.consts` values (empty = no constraint); `crawl_urls` is a **JSON list of listing URLs** (there is no `crawl_source` field — the source is derived from each URL's hostname); `status` from `profiles.consts.Status` ∈ {`waiting_payment`, `waiting_admin`, `running`, `expired`}, default `waiting_admin`. One Profile may have many Preferences.
- `jobs.Job` — job posting (`url` unique, `title`, `company`, `description`, `location`, `job_type`, `remote_option` from `jobs/consts.py`, `source`, plus `hard_skills`/`soft_skills` JSON lists filled by `extract_job_skills`). Legacy: does NOT inherit `BaseModel`.
- `jobs.CrawlHealthTarget` — a labelled listing URL + `source` probed by the `crawl_health_check` task. CRUD'd from the superuser admin at `/crawl-health/`.
- `assessment.Assessment` — joins `jobs.Job` + `profiles.Preference` (not Profile directly); unique constraint on `(job, preference)`. Carries skill match/gap JSON list fields (`soft_skill_match`, `soft_skill_gap`, `hard_skill_match`, `hard_skill_gap`), integer `score` (0-100), `is_relevant` bool, `status` from `assessment.consts.Status` (`new`/`seen`/`applied`/`rejected`/`accepted`), and a short LLM-authored `verdict` written in **casual Bahasa Indonesia using "kamu"** — enforced in the system prompt; preserve it when touching `assessment/services.py`.
- `billing.Plan` — `name`, `price` (IDR), `preference_limit`, `duration_days` (default 30 — subscription length is per-plan, **not** a hardcoded 30 days), `is_active`. `billing.Subscription` — Profile↔Plan with `SubscriptionStatus` ∈ {`PENDING`, `ACTIVE`, `EXPIRED`, `CANCELLED`, `REPLACED`}, Mayar fields (`payment_ref`, `payment_link`), `amount_paid`, and `replaces` (self-FK for upgrade chains).

Directional flow: **Profile + LinkedIn → Apify ingest → Preference (auto-filled `crawl_urls`, `WAITING_PAYMENT`) → payment → `RUNNING` → scrapers → Job → `check_relevance` → `assess()` → Assessment**.

### Crawl-source routing — `jobs/scrapers/`

Seven scrapers: `indeed.py`, `jobstreet.py`, `linkedin.py`, `dealls.py`, `kalibrr.py`, `kitalulus.py`, `karirhub.py`. Each exposes `crawl(url, max_pages=, limit=, sleep=)` as a generator of posting dicts. The last three are the "clean" sources (see `_docs/scraping-policy.md`): they identify themselves with `jobs.consts.BOT_USER_AGENT` and use `httpx`, no fingerprint impersonation. Kalibrr and Karirhub read public JSON APIs; Kitalulus parses schema.org JSON-LD.

`jobs/scrapers/__init__.py:scraper_for_url(url)` resolves `(module, Source value)` **by hostname** and returns `(None, None)` for unknown URLs. A Preference therefore never names its source — the URL does. Adding a board = one hostname branch here + a `profiles.consts.Source` member + a `CrawlHealthTarget.SOURCE_*` entry.

`jobs/scrapers/filters.py` drops postings from staffing/crowdwork brands (`BLOCKED_COMPANY_SUBSTRINGS = ("mindrift", "toloka")`) at each scraper's yield point.

`jobs/url_builders.py` builds the standard `crawl_urls` set for a Preference (`build_crawl_urls(title, job_types, remote_options)`): an Indeed query URL, a JobStreet URL (path slugs + `worktype`/`workarrangement` params), a LinkedIn SEA URL (geoId `91000014`), — **only when `remote` is among the remote options** — a second LinkedIn EMEA URL (geoId `91000007`) force-filtered to remote, since an on-site EMEA role is unreachable from Indonesia, and finally keyword-only URLs for Kalibrr, Kitalulus and Karirhub (those three expose no job-type/remote filter we can drive). Six URLs normally, seven for a remote-seeking preference.

### LinkedIn profile ingestion

`profiles/methods.py:crawl_and_ingest_linkedin` calls Apify, persists raw to `Profile.linkedin_raw`, then runs `profiles.services.ingest_linkedin` (LLM cleaner with `LinkedInIngest` Pydantic schema) which fills `full_profile`, `open_to_work`, and quality flags.

### Async pipeline (Celery)

`assessment/tasks.py`:

- `crawl_running_preferences()` — beat entrypoint. Selects Preferences where `status=RUNNING`, `crawl_urls` non-empty, **and** (the owning Profile has an `ACTIVE` Subscription with `expires_at > now` **OR** `profile.whitelist=True`). This gate is the paywall — don't loosen it without intent.
- `crawl_and_assess_preference(preference_id, reassess_existing=False)` — iterates every URL in `crawl_urls`, resolves the scraper via `scraper_for_url`, upserts `Job` rows by `url` inside `transaction.atomic` (`CRAWL_ITEM_LIMIT = 10` per URL), queues `extract_job_skills` for jobs with no skills yet, then queues `assess_job` per posting. With `reassess_existing=True` an already-assessed job is re-scored via `reassess_assessment` instead of skipped (off by default — it costs two extra LLM calls per seen job). Per-URL and per-posting failures are logged and skipped, never fatal.
- `assess_job(job_id, preference_id)` — idempotent. Runs `check_relevance` first (cheap LLM gate); if irrelevant, writes a stub Assessment with `is_relevant=False, score=0` and exits. Otherwise calls `assess()`. Publishes `assessment.created` to the user's Redis channel on create. `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`.
- `reassess_assessment(assessment_id)` — re-scores an existing Assessment in place, same retry policy. Triggered from the admin via `AssessmentReassessView` and by the reassess path above.
- `email_morning_high_score_summary()` — per-profile digest of today's `NEW`, relevant Assessments scoring ≥ `HIGH_SCORE_THRESHOLD` (80), day boundary computed in Asia/Jakarta.

`jobs/tasks.py`:

- `extract_job_skills(job_id)` — fills `Job.hard_skills`/`soft_skills` from the description via `jobs.services.extract_skills`. Idempotent (skips if either list is non-empty).
- `crawl_health_check()` — probes every active `CrawlHealthTarget` with a 5-item, 1-page crawl and posts a Discord report. Note `jobs.tasks.SCRAPERS` maps `CrawlHealthTarget.SOURCE_*` → `crawl` callables and is used **only** by this task; the production pipeline routes through `scraper_for_url`. Because the scrapers log-and-`break` on blocks rather than raising, `_probe` installs a temporary log handler on the `jobs.scrapers` logger so a zero-yield probe reports the real reason instead of a bare ❌.

`profiles/tasks.py`:

- `crawl_linkedin_for_profile(profile_id, preference_id=None)` — Apify ingest, then calls `prepare_preference_for_payment` for the profile's `WAITING_ADMIN` preferences that still have no `crawl_urls`.
- `notify_preference_created(preference_id)` — Discord ping (admin link built from `SITE_URL`).

`core/tasks.py` (payments):

- `poll_pending_subscriptions()` — beat sweep over PENDING subs created within 48h; activates or cancels based on Mayar status.
- `poll_subscription_after_checkout(subscription_id)` — aggressive self-rescheduling poll (every 30s for 10 min after checkout) as the webhook fallback.
- `expire_subscriptions()` — flips ACTIVE subs past `expires_at` to EXPIRED and cascades their profile's RUNNING Preferences to EXPIRED, but only for profiles not still covered by another live sub. Idempotent.

Beat schedules live in DB (`django_celery_beat.schedulers:DatabaseScheduler`) — register/edit via Django admin, not code. Broker/backend from env: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (defaults `redis://localhost:6379/{0,1}`).

### Preference lifecycle — the free crawl is disabled

`profiles/services.py:prepare_preference_for_payment(preference, *, require_full_profile=True)` auto-fills `crawl_urls` via `build_crawl_urls` and advances `WAITING_ADMIN → WAITING_PAYMENT`. It is idempotent and runs **no crawl** — the free registration crawl was removed. It is invoked from the `post_save` signal on `Preference` (`profiles/signals.py`), from `crawl_linkedin_for_profile`, and from the registration serializer with `require_full_profile=False` so a brand-new preference is payable before LinkedIn ingest finishes.

Consequence: the post-payment crawl is the *only* crawl a paying user gets on activation, which is why `activate_subscription` defensively backfills `crawl_urls` for any preference that reached `WAITING_PAYMENT` without them before queueing.

### Subscription / payment flow

- Frontend hits `POST /api/v1/subscriptions/checkout/` → backend creates a Mayar payment link, persists `Subscription(status=PENDING, payment_ref, payment_link)`, and kicks off `poll_subscription_after_checkout`.
- Mayar redirects the user to `PAYMENT_REDIRECT_URL`; the webhook to `/api/v1/payments/mayar/webhook/` (verified by `MAYAR_WEBHOOK_TOKEN` in `X-Callback-Token`) calls `core.payments.subscriptions.activate_subscription`.
- `activate_subscription` flips `PENDING→ACTIVE`, sets `expires_at = now + plan.duration_days` (+ upgrade bonus seconds), unlocks `WAITING_PAYMENT` Preferences to `RUNNING`, backfills missing `crawl_urls`, queues immediate crawls, and publishes `subscription.activated` on the user's Redis channel (consumed by the SSE stream).
- Design notes for this flow live in `docs/payment-mechanism.md`.
- Upgrades: `billing/upgrades.py:compute_upgrade_quote` / `prorate_upgrade` convert the old sub's unused value into bonus seconds on the new plan's window; on activation the old sub is marked `REPLACED` (expired immediately) and preference unlock is skipped (they're already RUNNING). Downgrades and same-plan are rejected (`UpgradeNotAllowed`).

### URLs / views

- `core/urls.py` mounts: `admin/`, `login/` (`AdminLoginView`), `logout/`, `dashboard/` (+ three HTMX-style fragment endpoints), `preferences/...` (incl. `crawl-now/`, `regenerate-urls/`, `regenerate-all-urls/`), `plans/...`, `subscriptions/...`, `crawl-health/...`, `settings/smtp-test/`, `assessments/`, `profiles/`, `jobs/`, `api/v1/`, and `/` → redirect to `/dashboard/`. All server-rendered admin views are superuser-gated (`SuperuserRequiredMixin` in `core/views.py`).
- `DashboardView` — superuser overview of Profile/Job/Assessment counts, top profiles, paginated recent assessments, and 30-day trends (Chart.js). Expensive sections are split into lazy fragment views and cached; `core/dashboard_cache.py` holds the day-scoped cache keys/TTLs and `core/signals.py` busts them `on_commit` when Assessment/Subscription/Profile/Preference rows change.
- DRF surface (consumed by the SPA) is at `api/v1/urls.py` — **top-level `api` package**, mounted at `/api/v1/`; impls split per domain (`auth_api.py`, `profiles_api.py`, `preferences_api.py`, `assessments_api.py`, `billing_api.py`, `payments_api.py`, `dashboard_api.py`, `landing_api.py`). Endpoints: public landing stats, auth (Google + token + `me`/`logout`), profile/onboarding, preferences, assessments, `payment-gate/`, plans, subscriptions (`me/`, `stream/` SSE, `checkout/`, `upgrade-quote/`, `cancel-pending/`, `<pk>/recheck/`), Mayar webhook, dashboard stats.
- Templates live at the project-root `templates/` dir (configured via `TEMPLATES.DIRS`), not per-app.
- `core/api/` holds only stale `__pycache__` — no live source. Ignore it; don't add endpoints there.

## Conventions

- Use `BaseModel` for new models so PKs stay BSON ObjectIds and audit fields are uniform.
- Each app declares `app_label` explicitly in `Meta` (mirrors existing models).
- Templates go in the project-root `templates/` dir, not per-app.
- New REST endpoints register under `api/v1/urls.py` (top-level `api` package), not at the project root or under `core/`.
- All OpenAI calls go through `core.openai.get_prompt_manager()` — don't instantiate `openai.OpenAI` directly in new code.
- The `verdict` field on Assessment is **Bahasa Indonesia, casual, "kamu"** by design. The assessor prompt also encodes a job-type / remote-option mismatch rule (cap score ~30 for one mismatch, ~15 for both, and say so in the verdict). Preserve both when editing `assessment/services.py`.
- `core.auth.EmailBackend` allows email-based login; preserve that contract when touching auth flows.
- The Celery pipeline gates crawls on **ACTIVE Subscription OR `profile.whitelist`**, not just Preference status — don't loosen this without intent.
- Scrapers must degrade gracefully: log + skip a bad posting, log + `break` on a block, never raise out of `crawl()`. `crawl_health_check` depends on those log records to explain failures.
- Custom template tag lib: `core/templatetags/format_number.py` — load with `{% load format_number %}`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, DB, Celery/Redis, OpenAI, Mayar, Google OAuth, Discord, SMTP (`EMAIL_*`, `DEFAULT_FROM_EMAIL`), `SITE_URL`, `FRONTEND_URL`, `APIFY_TOKEN`, and CORS/CSRF origins are read from env (see `.env.example` — note it currently omits `APIFY_TOKEN`, which `core/settings.py` does read). `SECRET_KEY` falls back to a hardcoded `django-insecure-` dev value; production boot raises `RuntimeError` if `DEBUG=False` and that fallback is still in use — never rely on that fallback in prod.
