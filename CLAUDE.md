# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Django 5.2, Python ≥3.10, DRF (`rest_framework` + `rest_framework.authtoken`). DRF defaults: `TokenAuthentication` + `IsAuthenticated` (`core/settings.py`).
- **Database**: Postgres in Docker / prod (`psycopg`); SQLite fallback for host dev. Selection is implicit in `core/settings.py` — if `POSTGRES_HOST` is set in env it uses Postgres, otherwise it falls back to `db.sqlite3` tuned with `journal_mode=WAL`, `synchronous=NORMAL`, `transaction_mode=IMMEDIATE`, `timeout=30`. Don't assume the dev DB is the prod DB.
- Dep mgmt via `uv` (`pyproject.toml`, `uv.lock`); lint/format via `ruff`. Frontend uses `pnpm`.
- Static: Whitenoise with `CompressedManifestStaticFilesStorage`; Tailwind v4 (`static/input.css` → `static/output.css`).
- Frontend SPA under `frontend/`: Vite + React 19 + TS, **TanStack Router** (file-based, generated `routeTree.gen.ts`) + **TanStack Query**, **Jotai** for state, **shadcn / Radix** + Tailwind v4 for UI. Talks to Django via `/api/v1/`.
- Celery + Redis for async work; `django_celery_beat` (`DatabaseScheduler`) for periodic tasks — schedules edited via Django admin, not code. `CELERY_TASK_ACKS_LATE=True`, `CELERY_TASK_REJECT_ON_WORKER_LOST=True`.
- LLM: `openai` SDK, structured output via `pydantic` (`SkillAssessment`, `RelevanceCheck`, `LinkedInIngest`). Model from `OPENAI_MODEL` (default `gpt-4o-2024-08-06`); cheap relevance gate uses `OPENAI_RELEVANCE_MODEL` (default `gpt-4o-mini`). All OpenAI calls go through `core.openai.get_prompt_manager()`.
- LinkedIn ingestion uses **Apify** (`apify-client`, actor `harvestapi/linkedin-profile-scraper`) — not a custom scraper.
- Auth: `core.auth.EmailBackend` (login by email) **plus** Google OAuth via `/api/v1/auth/google/` (verifies `GOOGLE_OAUTH_CLIENT_ID`).
- Payments: Mayar (`core/payments/mayar.py`) — payment-link create + webhook verified by `X-Callback-Token`.
- Realtime: Redis pub/sub (`core/realtime.py`) → SSE endpoint `/api/v1/subscriptions/stream/` (EventSource auth via `?token=` query param, since EventSource cannot set headers).
- Notifications:
  - Discord webhook (`core/notifications/discord.py`), called from Celery tasks; no-ops when `DISCORD_WEBHOOK_URL` is empty.
  - Transactional email (`core/notifications/email.py:send_email`) using Django's SMTP backend; no-ops with a warning when `EMAIL_HOST` / `EMAIL_HOST_USER` are unset. Daily summary task is `assessment.tasks.email_morning_high_score_summary` (registered via beat); links into the SPA use `FRONTEND_URL`. There's a superuser admin page at `/settings/smtp-test/` (`SmtpTestView`) that displays the live SMTP config and sends a test message.
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
```

`update.sh` is the prod deploy script: `git pull` → `docker compose build` → `up -d` → wait for postgres healthy → `manage.py migrate`. The Docker image runs `docker/backend-entrypoint.sh`, which branches on `ROLE` env (`web` runs `migrate` + `collectstatic` before exec'ing CMD; `worker` and `beat` skip those).

Direct Django (when Make target missing): `uv run manage.py <cmd>`.

Run a single test: `uv run manage.py test <app>.tests.<TestClass>.<test_method>` (e.g. `uv run manage.py test jobs.tests.JobModelTests.test_create`).

Job crawlers (management commands — one-shot ad hoc; recurring crawls run through the Celery pipeline below):

```sh
uv run manage.py crawl_indeed    "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
uv run manage.py crawl_jobstreet "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
```

Both upsert `Job` rows by `url` inside `transaction.atomic`. Defaults: `--max-pages 1`, `--limit 20`, `--sleep` from each scraper's `DEFAULT_SLEEP`.

## Architecture

Django project rooted at `core/` with four domain apps: `profiles`, `jobs`, `assessment`, `billing`. `core` is also installed as an app (holds `BaseModel` + `AppSetting`, the admin dashboard, the REST API surface, the Mayar payments adapter, Redis realtime, and Discord notifications). The `billing` app owns `Plan`, `Subscription`, `SubscriptionStatus`, and `effective_price` (Open-to-Work discount logic).

### Shared base — `core/models.py`

- `BaseModel` (abstract): primary key is a stringified BSON `ObjectId` (`make_object_id`), plus `created_on`, `updated_on`, optional `actor` FK to `auth.User`. Default ordering by `id`, index on `created_on`. **All new domain models should inherit from `BaseModel`** unless intentionally diverging (note: `jobs.Job` does NOT inherit — it duplicates the id/timestamp fields manually; treat as legacy and prefer `BaseModel` for new work).
- `AppSetting`: typed key/value store with `AppSetting.get(key, value_type, default)` for runtime config (`value_type` ∈ `str|int|float|bool`).

### Domain model shape

- `profiles.Profile` — candidate identity. Optional `OneToOne` to `auth.User`. Stores `linkedin_url`, `linkedin_raw` (Apify paste), `full_profile` (LLM-cleaned, fed to assessor), `open_to_work` (drives `linkedin_discount_eligible` → discount on the cheapest active plan, see `billing.effective_price`), `linkedin_quality_ok`/`linkedin_quality_reason`, and a `whitelist` flag that bypasses plan limits.
- `profiles.Preference` — candidate's job preference (FK `Profile`; `title`, `job_type`, `remote_option` from `jobs.consts`; `crawl_url`, `crawl_source` from `profiles.consts.Source` ∈ {INDEED, JOBSTREET}; `status` from `profiles.consts.Status` ∈ {`waiting_payment`, `waiting_admin`, `running`, `expired`}, default `waiting_admin`). One Profile may have many Preferences.
- `jobs.Job` — job posting (`url`, `title`, `company`, `description`, `location`, `JobType`, `RemoteOption` from `jobs/consts.py`, `source`). Legacy: does NOT inherit `BaseModel`.
- `assessment.Assessment` — joins `jobs.Job` + `profiles.Preference` (not Profile directly); unique constraint on `(job, preference)`. Carries skill match/gap JSON list fields (`soft_skill_match`, `soft_skill_gap`, `hard_skill_match`, `hard_skill_gap`), integer `score` (0-100), `is_relevant` bool, `status` from `assessment.consts.Status` (`new`/`seen`/`applied`/`rejected`/`accepted`), and a short LLM-authored `verdict` written in **casual Bahasa Indonesia using "kamu"** — this language constraint is enforced in the system prompt; preserve it when touching `assessment/services.py`.
- `billing.Plan` — `name`, `price` (IDR), `preference_limit`, `is_active`. `billing.Subscription` — Profile↔Plan with `SubscriptionStatus` ∈ {`PENDING`, `ACTIVE`, `EXPIRED`, `CANCELLED`, `REPLACED`}, plus Mayar fields (`payment_ref`, `payment_link`), `amount_paid`, and `replaces` (self-FK for upgrade chains).

Directional flow: **Profile + LinkedIn → Apify ingest → Preference (RUNNING, gated by ACTIVE Subscription) → scraper → Job → `check_relevance` → `assess()` → Assessment**.

### Ingestion

- Job postings: scraper logic in `jobs/scrapers/{indeed,jobstreet}.py`; thin `crawl_{indeed,jobstreet}` management commands wrap them for ad-hoc one-shot crawls.
- LinkedIn: `profiles/methods.py:crawl_and_ingest_linkedin` calls Apify, persists raw to `Profile.linkedin_raw`, then runs `profiles.services.ingest_linkedin` (LLM cleaner with `LinkedInIngest` Pydantic schema) which fills `full_profile`, `open_to_work`, and quality flags.

### Async pipeline (Celery)

Tasks in `assessment/tasks.py`:

- `crawl_running_preferences()` — beat entrypoint. Selects Preferences where `status=RUNNING` **AND** the owning Profile has an `ACTIVE` Subscription with `expires_at > now` AND `crawl_url`/`crawl_source` are non-empty. Subscription gating happens here — don't bypass it.
- `crawl_and_assess_preference(preference_id)` — picks scraper from `assessment.tasks.SCRAPERS` (`Source.INDEED` / `Source.JOBSTREET`), upserts `Job` rows by `url` inside `transaction.atomic`, queues `assess_job` per posting.
- `run_free_crawl(preference_id)` — one-shot free crawl + assess for a brand-new Preference, then flips its status to `WAITING_PAYMENT`. Kicked off by `maybe_start_free_crawl` (called from a `post_save` signal on Preference and from `crawl_linkedin_for_profile` after LinkedIn ingest completes); auto-fills `crawl_url` to `https://id.indeed.com/jobs?q=<title>` and `crawl_source=INDEED`.
- `assess_job(job_id, preference_id)` — idempotent. Runs `check_relevance` first (cheap LLM gate using `OPENAI_RELEVANCE_MODEL`); if irrelevant, writes a stub Assessment with `is_relevant=False, score=0` and exits. Otherwise calls `assess()`. `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`.
- `reassess_assessment(assessment_id)` — re-scores existing Assessment in place, same retry policy. Triggered from the admin via `AssessmentReassessView`.
- `profiles.tasks.crawl_linkedin_for_profile(profile_id, preference_id)` — runs Apify ingest, then opportunistically calls `maybe_start_free_crawl` for any pending preferences.
- `profiles.tasks.notify_preference_created(preference_id)` — Discord ping for new Preferences.

Beat schedules live in DB (`django_celery_beat.schedulers:DatabaseScheduler`) — register/edit via Django admin, not code. Broker/backend from env: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (defaults `redis://localhost:6379/{0,1}`).

### Subscription / payment flow

- Frontend hits `POST /api/v1/subscriptions/checkout/` → backend creates a Mayar payment link, persists `Subscription(status=PENDING, payment_ref, payment_link)`.
- Mayar redirects user to `PAYMENT_REDIRECT_URL` after pay; webhook to `/api/v1/payments/mayar/webhook/` (verified by `MAYAR_WEBHOOK_TOKEN` in `X-Callback-Token`) calls `core.payments.subscriptions.activate_subscription`.
- `activate_subscription` flips `PENDING→ACTIVE`, sets `expires_at = now + 30 days`, unlocks `WAITING_PAYMENT` Preferences to `RUNNING`, queues immediate crawls for already-configured ones, and publishes a `subscription.activated` event on the user's Redis channel (consumed by the SSE stream).
- Upgrades: `billing/upgrades.py:compute_upgrade_quote` computes prorated bonus seconds from the old sub's unused value; on activation the old sub is marked `REPLACED` and bonus seconds are appended to the new 30-day window. Downgrades and same-plan are explicitly rejected (`UpgradeNotAllowed`).
- `subscription_recheck` polls Mayar for status when the webhook is missed.

### URLs / views

- `core/urls.py` mounts: `admin/`, `login/` (`AdminLoginView`), `logout/`, `dashboard/`, `preferences/...`, `plans/...`, `subscriptions/...`, `assessments/`, `profiles/`, `jobs/`, `api/`, and `/` → redirect to `/dashboard/`. These server-rendered admin views are superuser-gated (`SuperuserRequiredMixin`).
- DRF surface (consumed by the SPA) is at `core/api/v1/urls.py` — auth (Google + token), profile/onboarding, preferences, assessments, plans, subscriptions (incl. `stream/` SSE, `checkout/`, `upgrade-quote/`, `cancel-pending/`, `<pk>/recheck/`), Mayar webhook, dashboard stats.
- `DashboardView` — superuser-gated admin overview of Profile/Job/Assessment counts, top profiles, paginated recent assessments, and 30-day trends rendered with Chart.js.
- Templates live at the project-root `templates/` dir (configured via `TEMPLATES.DIRS`), not per-app.

## Conventions

- Use `BaseModel` for new models so PKs stay BSON ObjectIds and audit fields are uniform.
- Each app declares `app_label` explicitly in `Meta` (mirrors existing models).
- Templates go in the project-root `templates/` dir, not per-app.
- New REST endpoints register under `core/api/v1/urls.py`, not at the project root.
- All OpenAI calls go through `core.openai.get_prompt_manager()` — don't instantiate `openai.OpenAI` directly in new code.
- The `verdict` field on Assessment is **Bahasa Indonesia, casual, "kamu"** by design — preserve the language rule when editing the assessor prompt.
- `core.auth.EmailBackend` allows email-based login; preserve that contract when touching auth flows.
- The Celery pipeline gates crawls on **ACTIVE Subscription**, not just Preference status — don't loosen this without intent.
- Custom template tag lib: `core/templatetags/format_number.py` — load with `{% load format_number %}`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, DB, Celery, OpenAI, Mayar, Google OAuth, Discord, SMTP (`EMAIL_*`, `DEFAULT_FROM_EMAIL`), `FRONTEND_URL`, Apify, and CORS/CSRF origins are all read from env (see `.env.example`). `SECRET_KEY` falls back to a hardcoded dev value — never rely on that fallback in prod.
- `main.py` is a leftover from `uv init` and unrelated to the Django app — ignore it.
