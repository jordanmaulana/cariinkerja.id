# About Cariinkerja

**Cariinkerja** is an AI job-search assistant built for Indonesia. Connect your LinkedIn, set your preferences once, and every day it crawls Indeed and JobStreet, scores each new posting from 0 to 100, and tells you exactly which skills match and which gaps to close — so you stop applying blind.

Live at [cariinkerja.id](https://cariinkerja.id).

---

## The problem

Job hunting in Indonesia still feels like 2010. You open Indeed in one tab, JobStreet in another, scroll past hundreds of postings, skim long JDs, copy-paste your resume into 200 forms, and hope something sticks.

The brutal part: most of those postings were never going to be a fit. Wrong stack, wrong seniority, wrong location, wrong contract type. You waste your evenings; recruiters waste their inbox. Nobody wins.

There has to be a better signal than "I applied to everything."

## What Cariinkerja does

We do the screening for you, every day, automatically.

1. **You connect LinkedIn.** We ingest your profile via Apify, then an LLM cleans and structures it into the shape our assessor needs.
2. **You set your preferences once.** Job title, remote vs. on-site, full-time vs. freelance, and which source to crawl (Indeed or JobStreet).
3. **A crawler runs daily for you.** Celery workers pull fresh postings matching your preferences. No more manual scrolling.
4. **An LLM scores every posting.** GPT-4o reads each job against your profile and returns a structured assessment: a 0–100 fit score, your matching hard and soft skills, the skill gaps you'd need to close, and a short verdict written in casual Bahasa Indonesia using "kamu."

You open the dashboard, sort by score, and focus on the 5–10 jobs that actually fit — instead of the 200 random ones in your inbox.

## What you get for every job

Each assessment includes:

- **Score 0–100** — how well your profile fits this specific posting.
- **Hard skills matched** — concrete technical skills the job asks for that you already have.
- **Hard skills missing** — the gaps. Useful for "what should I learn next" decisions.
- **Soft skills matched / missing** — the same, for communication, leadership, etc.
- **Verdict** — a short, plain-language summary in casual Bahasa ("kamu") explaining *why* this job fits or doesn't. No corporate-speak.
- **Status tracking** — mark jobs as seen, applied, accepted, or rejected as you work through them.

## Why a 0–100 score instead of a yes/no match

Gaps matter. A binary "match / no match" hides too much.

A score of **72 with two fixable skill gaps** is often a better lead than an **85 you'll never get a callback from**, because the 72 is something you can actually close in a few weeks of focused learning. We surface both numbers and the gap list so you can make that judgment yourself.

The verdict text gives you the human context: not just the number, but *why* the LLM thinks this is a fit or a stretch.

## Who it's for

- **Fresh graduates** unsure where to start or what's realistic to apply for. The score gives you a calibrated read on which postings are actually within reach.
- **Career switchers** who need a clear map of skill gaps before committing to an industry jump.
- **Busy candidates** — anyone already working full-time, freelancing, or studying who can't sit down and screen 200 postings a week manually.

## Sources we crawl

Today: **Indeed** and **JobStreet** (the two largest job boards in Indonesia). We add new sources based on user demand — let us know what you'd want next.

## Pricing

- **Free tier** — covers roughly your first 20 assessments so you can see if the signal is actually useful before paying.
- **30-day subscriptions** — pay-as-you-go, no annual lock-in. See [/plans](https://cariinkerja.id/plans) for current tiers.
- **Open-to-Work discount** — if you toggle "Open to Work" on your LinkedIn profile, our cheapest active plan is automatically discounted. If you're hunting hard, you shouldn't be paying full price.

## Our ethos

A few things we believe, and act on:

**Don't sell to people who can't afford it.** If subscribing would make your money situation worse, **don't subscribe.** Use the free tier, get your footing first. See [Before You Buy](beforeyoubuy.md) for the full version of this.

**Empty LinkedIn = bad assessments.** Garbage in, garbage out. Before you sign up, fill in your skills, write an honest "About," list real responsibilities under each role. Don't just put job titles. The quality of your matches is bounded by the quality of your profile.

**Sustainable, not predatory.** We'd rather have fewer paying users who get real value than a churn-and-burn funnel.

## Built in the open

Cariinkerja is open source under **[AGPL-3.0-or-later](LICENSE)**. If you want to see how the scoring works, audit how we handle your data, or self-host your own copy, the full source is on this repo.

**Stack:** Django 5.2 + DRF backend, React 19 + TanStack Router/Query SPA, Postgres, Celery + Redis for the async crawl/assess pipeline, Tailwind v4. Apify for LinkedIn ingest, OpenAI structured output (Pydantic schemas) for scoring, Mayar for payments, Google OAuth for sign-in.

If you're a developer interested in contributing or running it locally, see the [Development section of README.md](README.md#development) and [CLAUDE.md](CLAUDE.md) for the full architecture overview.

## Status

Live, in production, used by paying Indonesian job seekers every day. Public signups are open at **[cariinkerja.id](https://cariinkerja.id)**.

Questions, bug reports, feature ideas: open an issue on this repo. Security disclosures: see [SECURITY.md](SECURITY.md).

Before you buy: please read [Before You Buy](beforeyoubuy.md).
