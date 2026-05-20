# Cariinkerja — Product Hunt Launch Copy

## Name

Cariinkerja

## Tagline (≤60 chars)

**Primary**

AI scores every job 0–100 so you stop applying blind.

**Alternates**

- Daily AI job matches with skill gaps, in Bahasa.
- Cariin your fit. AI scores jobs so you don't spray.

## Short Description (≤260 chars)

Connect LinkedIn, set preferences once. Every day Cariinkerja crawls Indeed + JobStreet, scores each job 0–100, and shows which skills match and which gaps to close. Built for Indonesian seekers tired of spray-and-pray. Verdicts in casual Bahasa.

## First Maker Comment

Hai PH 👋

I built Cariinkerja because applying to jobs in Indonesia still feels like 2010 — open Indeed, open JobStreet, copy resume into 200 forms, hope one sticks.

**What it does**

- Paste your LinkedIn once. We ingest it via Apify + LLM cleanup.
- Set what you want: title, remote/on-site, full-time/freelance.
- Every day, a Celery crawler pulls fresh postings from Indeed + JobStreet.
- GPT-4o scores each one 0–100, lists your matched hard/soft skills, the gaps to close, and writes a short verdict in casual Bahasa using "kamu".

**Why 0–100 instead of binary match**

Gaps matter. A 72 with two fixable skills is often better than an 85 you'll never get a callback from. We surface both.

**Pricing**

Free tier covers ~20 assessments. Subs are 30-day. Toggle "Open to Work" on LinkedIn → automatic discount, because if you're job-hunting hard you shouldn't pay full price.

One thing we won't do: sell to people who can't afford it. The landing page literally tells struggling seekers to skip the subscription until they have momentum. Sustainable > predatory.

**Stack**

Django 5.2, DRF, Celery + Redis, React 19 + TanStack Router, OpenAI structured output via Pydantic. Code is AGPL-3.0.

Would love feedback from anyone who's job-hunted in SEA — does the 0–100 + skill-gap framing actually help, or do you want a different signal?

— Jordan

## Topics / Tags

Pick 3 on submission (add SaaS if PH allows 4):

- Artificial Intelligence
- Career
- Hiring & Recruiting
- SaaS
