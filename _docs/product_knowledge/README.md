# Product Knowledge — cariinkerja.id

*Last verified against code and with the founder: 2026-10-22.*

**Who this is for:** AI agents (and people) planning social media posts, ads, launch copy,
or any other non-code work for cariinkerja.id. Read this folder before writing anything
public about the product.

**Rule of precedence:** where this folder disagrees with any other doc, deck, video, or
older copy, **this folder wins**. Before stating a *new* fact that isn't here, verify it in
the code (or ask the founder) and add it here.

## Read order

1. **This file**: fact sheet and the checklist to run before every post.
2. [product.md](product.md): what the product is, how it works, pricing, ethos, known drift.
3. [brand-voice.md](brand-voice.md): logo, colours, Open Graph image, the founder's voice, and approved copy quoted word for word.
4. [marketing-playbook.md](marketing-playbook.md): audiences, messages, content pillars, proof points, assets, channels, guardrails, and stale claims to avoid.
5. [og-image.png](og-image.png): the current Open Graph / link-preview image (1200×630). It's a copy; the live one is `frontend/public/og-image.png`.

## Fact sheet

| | |
|---|---|
| **Product** | cariinkerja.id: AI job-matching assistant for Indonesian job seekers |
| **URL** | https://cariinkerja.id |
| **One-liner (live hero)** | "Cariin kamu loker yang cocok, biar kamu ga capek cari sendiri." |
| **What it does** | User connects LinkedIn and sets a search (job title + job type + remote option). Every day at **05:00 WIB** it crawls new postings, drops obviously irrelevant ones, and scores each remaining one **0–100** against the profile. Each score comes with the hard/soft skills matched, the **skill gap**, and a short verdict in casual Bahasa ("kamu"). At **09:00 WIB** the user gets an email if any new match scored **80+**. |
| **Core idea** | A decision tool, not a match flag: apply to the ~5 jobs that fit instead of 200 random ones. |
| **Audience** | Indonesian fresh graduates, career switchers, and busy candidates who can't screen 200 postings a week. |
| **Language** | Bahasa Indonesia UI and copy, casual "kamu". Job/tech terms stay English (apply, skill gap). |
| **Business model** | **Paid-only. No free tier, no trial.** The first crawl happens after payment. |
| **Pricing** | **Rp 49.000 / 30 days → 1 search (job title)** · **Rp 99.000 / 30 days → 3 searches**. Payment via Mayar (Indonesian gateway). |
| **Job sources (live)** | Indeed Indonesia, JobStreet Indonesia, LinkedIn Southeast Asia, LinkedIn EMEA (remote roles only). Kalibrr + Kitalulus are on an unmerged branch; **don't announce them**. |
| **Sign-up** | Google sign-in only. Four honesty checkboxes must be ticked first (see brand-voice.md). |
| **Team** | Solo founder: **Jordan (Jordan Maulana)**, who builds, runs, and markets it. |
| **Open source** | AGPL-3.0, public repo: https://github.com/jordanmaulana/cariinkerja.id |
| **Brand socials** | **None exist yet.** Existing presence: founder LinkedIn (https://www.linkedin.com/in/jordan-maulana/) and the GitHub repo. |
| **Support** | WhatsApp admin `https://wa.me/6285138530082` (linked inside the app only) · `security@cariinkerja.id` |
| **Live public stats** | `GET https://cariinkerja.id/api/v1/landing/stats/`: profiles, jobs, assessments, highly suitable (80+), each with total and today. No login needed. |

## Pre-post checklist

Run this on every caption, script, ad, or thread before it goes out:

1. **No "gratis", "free", "trial", or "coba dulu".** The product is paid-only.
2. **Prices come only from this folder.** Older docs and the pitch deck show retired prices. The Open-to-Work discount is live: Rp 15.000 off the 1-search plan (Rp 34.000).
3. **Name job sources only if they're still live.** Check `jobs/url_builders.py` on `main`. When in doubt, say "loker dari berbagai job board", as the ad script does.
4. **Every traction number carries its date.** Use the snapshot date, or pull fresh numbers from the live stats endpoint.
5. **Never name the AI model** ("GPT-4o" etc.); just say "AI". **Never promise a job or an interview.**

Full guardrails: [marketing-playbook.md § Guardrails](marketing-playbook.md#7-guardrails).

## Keeping this folder true

Update it in the same change whenever any of these move:
- plan prices or plan count (admin)
- job sources (`jobs/url_builders.py`, the landing `source-strip.tsx`)
- landing copy (`frontend/src/features/landing/`)
- the OG image (`frontend/public/og-image.png`): re-copy it here
- schedules (beat migrations)

Bump the *Last verified* date at the top of each file you touch.
