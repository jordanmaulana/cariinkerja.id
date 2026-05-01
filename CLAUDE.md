# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Django 5.2, Python ≥3.10, SQLite (`db.sqlite3`) tuned with `journal_mode=WAL`, `synchronous=NORMAL`, `transaction_mode=IMMEDIATE`, `timeout=30` (`core/settings.py:106-110`).
- Dep mgmt via `uv` (`pyproject.toml`, `uv.lock`); lint/format via `ruff`.
- Static: Whitenoise with `CompressedManifestStaticFilesStorage`; Tailwind v4 wired (`static/input.css` → `static/output.css`).
- Frontend SPA under `frontend/` (Vite + React + TS + TanStack, pnpm). Separate from Django server-rendered templates; talks to backend via DRF endpoints under `/api/`.
- DRF installed (`rest_framework`, `rest_framework.authtoken`). Defaults: `TokenAuthentication` + `IsAuthenticated` (`core/settings.py:59-66`).
- Celery + Redis for async work; `django_celery_beat` (DatabaseScheduler) for periodic tasks — schedules edited via Django admin, not code.
- `pydantic` used for OpenAI structured output (`SkillAssessment` schema in `assessment/services.py`).
- `openai` SDK is the producer of Assessment skill JSON fields and `verdict`.
- Custom auth backend `core.auth.EmailBackend` lets users sign in by email (alongside `ModelBackend`).
- `TIME_ZONE = "Asia/Jakarta"` for both Django and Celery (`USE_TZ=True`).

## Common commands

All via `Makefile` (uses `uv run`):

```
make dev        # runserver on :8000
make mmg        # makemigrations
make migrate    # migrate
make lint       # ruff format + ruff check --fix
make upgrade    # uv sync + uv lock --upgrade
make tw-run     # tailwind watch
make tw-build   # tailwind one-shot build
make web        # cd frontend && pnpm run dev
make worker     # celery -A core worker -l info
make beat       # celery -A core beat -l info
make audit      # cd frontend && pnpm audit fix
```

Direct Django (when Make target missing): `uv run manage.py <cmd>`.

Run a single test: `uv run manage.py test <app>.tests.<TestClass>.<test_method>` (e.g. `uv run manage.py test jobs.tests.JobModelTests.test_create`).

Job crawlers (management commands — one-shot; the recurring path is the Celery pipeline below):

```
uv run manage.py crawl_indeed    "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
uv run manage.py crawl_jobstreet "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
```

Both upsert `Job` rows by `url` inside a `transaction.atomic` block. Defaults: `--max-pages 1`, `--limit 20`, `--sleep` from each scraper's `DEFAULT_SLEEP`.

## Architecture

Django project rooted at `core/` with three domain apps: `profiles`, `jobs`, `assessment`. `core` is also installed as an app (holds `BaseModel` + `AppSetting` + dashboard + REST API surface).

### Shared base — `core/models.py`

- `BaseModel` (abstract): primary key is a stringified BSON `ObjectId` (`make_object_id`), plus `created_on`, `updated_on`, optional `actor` FK to `auth.User`. Default ordering by `id`, index on `created_on`. **All new domain models should inherit from `BaseModel`** unless intentionally diverging (note: `jobs.Job` currently does NOT inherit — it duplicates the id/timestamps fields manually; treat as legacy and prefer `BaseModel` for new work).
- `AppSetting`: typed key/value store with `AppSetting.get(key, value_type, default)` helper for runtime config (`value_type` ∈ `str|int|float|bool`).

### Domain model shape

- `profiles.Profile` — candidate identity (`full_name`, `linkedin_url`, `bio`, `full_profile`). Optional `OneToOne` `user` → `auth.User`. `full_profile` is admin-filled long-form context fed to the LLM at assessment time.
- `profiles.Preference` — candidate's job preference (FK `Profile`; `title`, `job_type`, `remote_option` from `jobs/consts.py`; `crawl_url`, `crawl_source` from `profiles.consts.Source` ∈ {INDEED, JOBSTREET}; `status` from `profiles.consts.Status`, default `WAITING_PAYMENT`). One Profile may have many Preferences. The Celery pipeline only crawls preferences with `status=RUNNING` and non-empty `crawl_url`/`crawl_source`.
- `jobs.Job` — job posting (`url`, `title`, `company`, `description`, `location`, `JobType`, `RemoteOption` from `jobs/consts.py`, `source`). Legacy: does NOT inherit `BaseModel`.
- `assessment.Assessment` — joins `jobs.Job` + `profiles.Preference` (not Profile directly) with skill match/gap JSON list fields (`soft_skill_match`, `soft_skill_gap`, `hard_skill_match`, `hard_skill_gap`), integer `score` (0-100), and a short LLM-authored `verdict`. Produced by `assessment.services.assess()` via OpenAI structured output (`SkillAssessment` Pydantic schema, model from `settings.OPENAI_MODEL`, default `gpt-4o-2024-08-06`).

Directional flow: **Preference (RUNNING) → scraper → Job → `assess()` → Assessment**.

### Ingestion (Indeed / JobStreet)

- Scraper logic: `jobs/scrapers/{indeed,jobstreet}.py` (HTTP fetch, parsing, normalization).
- Django wrappers: `jobs/management/commands/crawl_{indeed,jobstreet}.py` — thin commands that invoke the scrapers and upsert `Job` rows. Used for ad-hoc one-shot crawls; recurring crawls run through the Celery pipeline.

### Async pipeline (Celery)

Tasks live in `assessment/tasks.py`:

- `crawl_running_preferences()` — beat entrypoint; fans out one `crawl_and_assess_preference` per `Preference` with `status=RUNNING` and crawl config.
- `crawl_and_assess_preference(preference_id)` — picks the scraper from `assessment.tasks.SCRAPERS` (`Source.INDEED` / `Source.JOBSTREET`), upserts `Job` rows by `url` inside `transaction.atomic`, queues `assess_job` per posting.
- `assess_job(job_id, preference_id)` — idempotent (no-op if Assessment exists); calls `assessment.services.assess()`. `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`.
- `reassess_assessment(assessment_id)` — re-scores existing Assessment in place, same retry policy.

Beat schedules live in DB (`django_celery_beat.schedulers:DatabaseScheduler`) — register/edit via Django admin, not code. Broker/backend from env: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (defaults `redis://localhost:6379/{0,1}`). `CELERY_TASK_ACKS_LATE=True`, `CELERY_TASK_REJECT_ON_WORKER_LOST=True`.

### URLs / views

- `core/urls.py` mounts: `admin/`, `login/` (`AdminLoginView`), `logout/` (Django `LogoutView`, `next_page="login"`), `dashboard/` (`DashboardView`), `preferences/...` (preference list/detail/`crawl-now`, views in `core/views.py`), and `/` → redirect to `/dashboard/`.
- App-level routers exist and are included from `core/urls.py`:
  - `assessments/` → `assessment.urls` (list/detail/reassess; `AssessmentReassessView` triggers `reassess_assessment.delay()`).
  - `profiles/` → `profiles.urls` (list/detail).
  - `jobs/` → `jobs.urls` (list/detail).
  - `api/` → `core.api.urls` → `core.api.v1` (`serializers.py`, `views.py`, `urls.py`) — DRF surface for the `frontend/` SPA.
- `DashboardView` — superuser-gated (`SuperuserRequiredMixin`) admin overview of Profile/Job/Assessment counts, top profiles, paginated recent assessments, and 30-day trends rendered with Chart.js.
- Templates live at the project-root `templates/` dir (configured via `TEMPLATES.DIRS`), not per-app:
  - `templates/dashboard.html` extends `templates/dashboard_base.html`.
  - `templates/registration/login.html`.
  - `templates/{assessments,jobs,profiles,preferences}/{list,detail}.html`.
  - `templates/admin/` for admin overrides (currently empty).

## Conventions

- Use `BaseModel` for new models so PKs stay BSON ObjectIds and audit fields are uniform.
- Each app declares `app_label` explicitly in `Meta` (mirrors existing models).
- Templates go in the project-root `templates/` dir, not per-app.
- New REST endpoints register under `core/api/v1/urls.py`, not at the project root.
- Custom template tag lib: `core/templatetags/format_number.py` — load with `{% load format_number %}`.
- `core.auth.EmailBackend` allows email-based login; preserve that contract when touching auth flows.
- Settings file is dev-only: `DEBUG=True`, secret key inline, `ALLOWED_HOSTS=[]`. Do not assume prod-ready config.
- `main.py` is a leftover from `uv init` and unrelated to the Django app — ignore it.
