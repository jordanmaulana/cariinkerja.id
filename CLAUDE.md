# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Django 5.2 + Django REST Framework, Python ≥3.10, SQLite (`db.sqlite3`).
- Dependency mgmt via `uv` (see `pyproject.toml`, `uv.lock`).
- Lint/format via `ruff`.
- Frontend dir exists (`frontend/`) but is empty; pnpm + Tailwind targets defined in Makefile but `static/input.css` not yet present.
- `openai` SDK is a dependency (assessment scoring is the likely consumer).

## Common commands

All via `Makefile` (uses `uv run`):

```
make dev        # runserver on :8000
make mmg        # makemigrations
make migrate    # migrate
make lint       # ruff format + ruff check --fix
make upgrade    # uv sync + uv lock --upgrade
make tw-run     # tailwind watch (needs static/input.css)
make tw-build   # tailwind one-shot build
make web        # cd frontend && pnpm run dev
```

Direct Django (when Make target missing): `uv run manage.py <cmd>`.

Run a single test: `uv run manage.py test <app>.tests.<TestClass>.<test_method>` (e.g. `uv run manage.py test jobs.tests.JobModelTests.test_create`).

## Architecture

Django project rooted at `core/` with three domain apps: `profiles`, `jobs`, `assessment`. `core` is also installed as an app (holds `BaseModel` + `AppSetting`).

### Shared base — `core/models.py`

- `BaseModel` (abstract): primary key is a stringified BSON `ObjectId` (`make_object_id`), plus `created_on`, `updated_on`, optional `actor` FK to `auth.User`. Default ordering by `id`, index on `created_on`. **All new domain models should inherit from `BaseModel`** unless intentionally diverging (note: `jobs.Job` currently does NOT inherit — it duplicates the id/timestamps fields manually; treat as legacy and prefer `BaseModel` for new work).
- `AppSetting`: typed key/value store with `AppSetting.get(key, value_type, default)` helper for runtime config (`value_type` ∈ `str|int|float|bool`).

### Domain model shape

- `profiles.Profile` — candidate side (full_name, bio).
- `jobs.Job` — job posting (url, title, description, location, `JobType`, `RemoteOption` from `jobs/consts.py`).
- `assessment.Assessment` — joins a `Job` and a `Profile` with skill match/gap JSON fields (`soft_skill_match`, `soft_skill_gap`, `hard_skill_match`, `hard_skill_gap`) plus integer `score`. This is the matching/scoring artifact between a profile and a job.

The directional flow is: Profile + Job → Assessment (gap analysis + score). LLM calls (openai dep) are the expected producer of the JSON skill fields.

### URLs / views

`core/urls.py` only routes `admin/` so far. App-level `urls.py` files don't exist yet — add per-app routers and include them in `core/urls.py` when wiring endpoints. DRF is installed but not yet configured in `INSTALLED_APPS` (`rest_framework` missing) — add it before using DRF features.

## Conventions

- Use `BaseModel` for new models so PKs stay BSON ObjectIds and audit fields are uniform.
- Each app declares `app_label` explicitly in `Meta` (mirrors existing models).
- Settings file is dev-only: `DEBUG=True`, secret key inline, `ALLOWED_HOSTS=[]`. Do not assume prod-ready config.
- `main.py` is a leftover from `uv init` and unrelated to the Django app — ignore it.
