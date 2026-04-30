# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Django 5.2, Python ≥3.10, SQLite (`db.sqlite3`).
- Dep mgmt via `uv` (`pyproject.toml`, `uv.lock`); lint/format via `ruff`.
- Static: Whitenoise with `CompressedManifestStaticFilesStorage`; Tailwind v4 wired (`static/input.css` → `static/output.css`).
- Frontend SPA scaffold under `frontend/` (Vite + React + TS + TanStack, pnpm). Separate from Django server-rendered templates.
- `djangorestframework` is a dependency but **not yet** in `INSTALLED_APPS` and unused — add `"rest_framework"` before introducing serializers/viewsets.
- `openai` SDK present; expected producer of Assessment skill JSON fields.

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
```

Direct Django (when Make target missing): `uv run manage.py <cmd>`.

Run a single test: `uv run manage.py test <app>.tests.<TestClass>.<test_method>` (e.g. `uv run manage.py test jobs.tests.JobModelTests.test_create`).

Job crawlers (management commands):

```
uv run manage.py crawl_indeed    "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
uv run manage.py crawl_jobstreet "<listing-url>" [--max-pages N] [--limit N] [--sleep S] [--dry-run]
```

Both upsert `Job` rows by `url` inside a `transaction.atomic` block. Defaults: `--max-pages 1`, `--limit 20`, `--sleep` from each scraper's `DEFAULT_SLEEP`.

## Architecture

Django project rooted at `core/` with three domain apps: `profiles`, `jobs`, `assessment`. `core` is also installed as an app (holds `BaseModel` + `AppSetting` + dashboard).

### Shared base — `core/models.py`

- `BaseModel` (abstract): primary key is a stringified BSON `ObjectId` (`make_object_id`), plus `created_on`, `updated_on`, optional `actor` FK to `auth.User`. Default ordering by `id`, index on `created_on`. **All new domain models should inherit from `BaseModel`** unless intentionally diverging (note: `jobs.Job` currently does NOT inherit — it duplicates the id/timestamps fields manually; treat as legacy and prefer `BaseModel` for new work).
- `AppSetting`: typed key/value store with `AppSetting.get(key, value_type, default)` helper for runtime config (`value_type` ∈ `str|int|float|bool`).

### Domain model shape

- `profiles.Profile` — candidate identity (`full_name`, `bio`).
- `profiles.Preference` — candidate's job preference (FK `Profile`; `title`, `job_type`, `remote_option` from `jobs/consts.py`). One Profile may have many Preferences; each Preference is what gets matched against a Job.
- `jobs.Job` — job posting (`url`, `title`, `description`, `location`, `JobType`, `RemoteOption` from `jobs/consts.py`). Legacy: does NOT inherit `BaseModel`.
- `assessment.Assessment` — joins `jobs.Job` + `profiles.Preference` (not Profile directly) with skill match/gap JSON list fields (`soft_skill_match`, `soft_skill_gap`, `hard_skill_match`, `hard_skill_gap`) plus integer `score`.

Directional flow: **Preference + Job → Assessment** (gap analysis + score). LLM calls (openai dep) are the expected producer of the JSON skill fields.

### Ingestion (Indeed / JobStreet)

- Scraper logic: `jobs/scrapers/{indeed,jobstreet}.py` (HTTP fetch, parsing, normalization).
- Django wrappers: `jobs/management/commands/crawl_{indeed,jobstreet}.py` — thin commands that invoke the scrapers and upsert `Job` rows.

### URLs / views

- `core/urls.py` routes: `admin/`, `login/` (`AdminLoginView`), `logout/` (Django `LogoutView`, `next_page="login"`), `dashboard/` (`DashboardView`), and `/` → redirect to `/dashboard/`.
- `DashboardView` in `core/views.py` — superuser-gated (`SuperuserRequiredMixin`) admin overview of Profile/Job/Assessment counts, top profiles, paginated recent assessments, and 30-day trends rendered with Chart.js.
- Templates live at the project-root `templates/` dir (configured via `TEMPLATES.DIRS`), not per-app: `templates/dashboard.html` extends `templates/dashboard_base.html`; `templates/registration/` holds the login template; `templates/admin/` holds admin overrides.
- No app-level `urls.py` yet — wire per-app routers and include from `core/urls.py` when adding endpoints.

## Conventions

- Use `BaseModel` for new models so PKs stay BSON ObjectIds and audit fields are uniform.
- Each app declares `app_label` explicitly in `Meta` (mirrors existing models).
- Templates go in the project-root `templates/` dir, not per-app.
- Settings file is dev-only: `DEBUG=True`, secret key inline, `ALLOWED_HOSTS=[]`. Do not assume prod-ready config.
- `main.py` is a leftover from `uv init` and unrelated to the Django app — ignore it.
