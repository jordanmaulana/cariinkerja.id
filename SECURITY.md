# Security Policy

## Supported versions

This project is under active development on the `main` branch. Security fixes are applied to `main` only; there are no maintained release branches.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security reports.

Email **security@cariinkerja.id** with:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept code, requests, or screenshots)
- The affected component (backend, SPA, Celery pipeline, etc.) and any relevant version/commit
- Your contact info for follow-up

We aim to acknowledge reports within **3 business days** and provide a remediation timeline within **10 business days**. Please give us a reasonable window to ship a fix before public disclosure.

## Scope

In scope:

- The Django backend (`core/`, `profiles/`, `jobs/`, `assessment/`, `billing/`)
- The SPA under `frontend/`
- The Celery task pipeline and its inputs (Apify ingest, scrapers, LLM prompts)
- Authentication flows (Google OAuth, email/password, token issuance)
- Mayar payment webhook handling

Out of scope:

- Third-party services (Apify, Mayar, OpenAI, Google) — report to those vendors directly
- Self-hosted forks running modified code
- Issues that require physical access or already-compromised credentials

## Hardening checklist for self-hosters

If you deploy this project, at minimum:

- Set a strong `SECRET_KEY` (the dev fallback is rejected at boot when `DEBUG=False`)
- Run with `DEBUG=False` and a real `DJANGO_ALLOWED_HOSTS` list
- Verify `MAYAR_WEBHOOK_TOKEN` is set if you accept payments
- Restrict `DJANGO_CORS_ALLOWED_ORIGINS` to your real frontend origin
- Keep dependencies updated (`make upgrade`, `make audit`)
