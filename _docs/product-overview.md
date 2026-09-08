# Product Overview — cariinkerja.id

**Read this first.** It describes *what the product is* and *why it behaves the way it
does*. It contains no code. For architecture see `CLAUDE.md`; for billing internals see
`payment-mechanism.md` in this folder.

Where this doc and the marketing files (`about.md`, `producthunt.md`, the landing page)
disagree, **this doc is correct** — see §8.

---

## 1. What it is

An AI job-search assistant for Indonesia.

You connect your LinkedIn once and describe the job you want. Every day the product pulls
fresh postings from Indonesian and international job boards, scores each one **0–100**
against your actual profile, lists the skills you already match and the ones you're
missing, and writes a short plain-language verdict explaining the number.

You open one queue, sort by score, and apply to the five jobs that fit — instead of the
two hundred you'd otherwise spray.

The core design choice: **it is not a match flag, it is a decision tool.** Every posting
gets a number and a reason, not a yes/no.

Live in production at cariinkerja.id. Open source, AGPL-3.0.

---

## 2. The problem

Job hunting in Indonesia still works like 2010. Open Indeed in one tab, JobStreet in
another, scroll hundreds of listings, skim long JDs, paste your resume into two hundred
forms, hope.

Most of those postings were never going to be a fit — wrong stack, wrong seniority, wrong
location, wrong contract type. The candidate burns their evenings; the recruiter burns
their inbox. Nobody wins.

### Why 0–100 and not "match / no match"

A binary flag hides the part that matters: **the gap**.

A **72 with two closeable skill gaps** is often a better lead than an **85 you'll never get
a callback from** — because the 72 is something you can act on in a few weeks of focused
learning. The product surfaces the score *and* the gap list *and* the reasoning, and lets
the person make that judgment themselves.

This is also why the dashboard exists: to show your own search momentum honestly. Its
framing is *"buat refleksi, bukan flexing"* — for reflection, not for flexing.

---

## 3. Who it's for

- **Fresh graduates** who don't know where to start or what's realistically within reach.
  The score gives them a calibrated read.
- **Career switchers** who need a concrete map of skill gaps before committing to an
  industry jump.
- **Busy candidates** — already working, freelancing, or studying — who cannot sit down and
  screen 200 postings a week by hand.

**Indonesia-first, not translated into Indonesian.** Indonesian job boards, Bahasa
Indonesia UI, IDR pricing, LinkedIn-native onboarding, an Indonesian payment gateway, and
verdicts written in casual Bahasa using *"kamu"*. The tone throughout is deliberately
colloquial and unpolished — closer to how a friend talks than how a SaaS talks.

---

## 4. How it works, from the user's side

1. **Sign in with Google.** No manual registration — the account is created on first
   sign-in. But before the sign-in button becomes clickable, the user must tick four
   checkboxes acknowledging: fill in your LinkedIn properly, be honest in it, *don't sign up
   if you're financially struggling*, and *this is a paid service with no trial*.
2. **Onboarding — one form.** Full name, phone number (needed later for payment), LinkedIn
   URL (required), optional bio, plus the first search: job title, job types, remote
   options. Nothing is charged here.
3. **The LinkedIn profile is ingested and cleaned** in the background — pulled via a
   scraping service, then rewritten by an LLM into the structured shape the scorer needs.
   This step also detects whether the profile is too sparse to score well, and whether the
   person has "Open to Work" enabled.
4. **Subscribe.** A search does nothing until it's paid for. Two gates can block checkout
   (§6).
5. **Every day it works for you.** A crawl runs each morning, new postings get scored, and
   high-scoring matches are emailed. The user reviews the queue, opens what looks good, and
   marks what they applied to.

Two friction points are **intentional**: the pre-sign-in checklist, and the payment gate
that refuses money from users whose profile is too thin to produce good scores. See §7.

---

## 5. Features

### Searches ("Pencarian")

A search is what the user configures: a job title, optional job types (full-time, part-time,
contract, internship), and optional remote options (remote, on-site, hybrid). Leaving a
filter empty means "no constraint".

One search automatically fans out to every supported source — the user never assembles a
board URL or picks a site. How many searches you can keep is capped by your plan tier.

Editing a running search pauses it and sends it back for admin review before it resumes.
Searches can only be deleted while unpaid.

### Sources

Five integrations: **Indeed Indonesia**, **JobStreet Indonesia**, **LinkedIn Southeast
Asia**, **LinkedIn EMEA**, and **Dealls**.

LinkedIn EMEA is only searched for *remote* roles — an on-site European or Middle Eastern
job is unreachable for an Indonesian candidate, so including it would be noise.

Certain staffing and crowdwork brands are filtered out of results entirely as low-quality
listings.

### Daily matching

Each morning (05:00 WIB) every paid, running search is crawled. New postings pass a cheap
relevance check first — an obviously wrong posting is discarded before it costs a full
scoring pass, and it never appears in the user's list at all. What survives gets fully
assessed.

### Per-job assessment

Each assessed posting produces:

- **Score 0–100** — how well the profile fits *this* posting.
- **Hard skills matched / missing** — the concrete technical gap.
- **Soft skills matched / missing** — the same for communication, leadership, and so on.
- **Verdict** — one to three sentences explaining the score in plain language.

**The verdict is always casual Bahasa Indonesia using "kamu", even when both the job and the
profile are in English.** This is a product rule, not an implementation detail. Skill names
stay in their short English technical form.

Scoring rules the user can feel: if a posting mismatches their job-type or remote
preference, the score is capped hard (roughly 30 for one mismatch, roughly 15 for both) and
the mismatch is named explicitly in the verdict — so a low score is never unexplained.

Postings are also parsed for their own required hard and soft skills.

### Pipeline tracking

Every match carries a status the user moves forward: **new → seen → applied → accepted**,
with **rejected** available as a terminal branch at any point.

Transitions are **forward-only and irreversible by design** — rejecting hides the job from
the queue and only support can bring it back. The point is an honest record of what you
actually did, not a task board you can groom.

### Dashboard

Total matches, matches added today, average score, active searches, plus a 30-day activity
trend, a score distribution across four buckets, a status breakdown, and the five most
recent matches.

### Daily email

At 09:00 WIB, users with new **high-fit** matches (score **80 or above**) get one email
telling them how many landed, linking straight into the filtered list. No email on a quiet
day.

### Realtime updates

An open tab updates itself: subscription activation, newly created assessments, status
changes, and search status changes all arrive without a refresh. Notably, the app never
trusts the payment gateway's redirect — an activated subscription is confirmed by a pushed
event or a manual "I already paid, refresh" button.

### Operator tools

The product is run by a single operator, and a large server-rendered admin surface exists
for that: reviewing and approving searches, inspecting and repairing profiles (including
hand-writing a profile when scraping fails), re-running an assessment, managing plans and
subscriptions manually, and a daily automated health check on every scraper reported to
Discord. Crawlers break often — sources actively block scraping — so this operator layer is
load-bearing, not a bolt-on.

---

## 6. Business model

**Paid-only. There is no free tier and no trial.** The first crawl happens *after* payment.
A user who signs up and never subscribes gets an onboarded account and nothing else.

### Plans

All plans run **30 days**, priced in IDR:

| Plan | Price | Searches |
|---|---|---|
| Basic | Rp 99,000 | 1 |
| Walker | Rp 159,000 | 3 |
| Runner | Rp 239,000 | 5 |

Each plan includes daily matching and AI scoring; the tier only changes how many
simultaneous searches you can run.

### Open-to-Work discount

If your LinkedIn has "Open to Work" enabled, the **cheapest plan** drops to **Rp 49,000** —
roughly half. The reasoning is stated plainly to the user: if you're hunting hard, you
shouldn't be paying full price.

It applies to new subscriptions only, not renewals, and only to the cheapest plan.

### Upgrades, downgrades, expiry

- **Upgrade**: you pay the new plan's full price, and whatever value was left on your old
  subscription is converted into **bonus days** on the new one. No refunds, no credit
  balance — just a later expiry date. The final bonus is calculated at payment time, so
  paying later means slightly fewer bonus days.
- **Downgrade**: rejected outright. Wait for the current plan to expire.
- **Expiry**: when a subscription lapses, its searches stop running.

### Two gates that block payment

The product will refuse to take money in two situations:

1. **Thin LinkedIn profile.** If the ingested profile is too sparse to score against, the
   user is told to fill it in and resubmit before subscribing. Garbage in, garbage out — and
   charging for garbage output is not acceptable.
2. **Search still under review.** While a new search is being prepared, checkout is locked
   with the message: *wait, we're still collecting jobs — see the results first, then buy.*

### Comped access

An admin whitelist flag exists that bypasses both the subscription requirement and the
plan's search limit. Used for comped and internal accounts.

---

## 7. Product constraints not to "optimize away"

Several things in this product look like conversion friction and are not. Removing them
would raise signups and destroy the positioning:

- **The four-checkbox gate before sign-in**, including *"don't sign up if you're financially
  struggling"* and *"this is a paid service, no trial"*. It filters out users the product
  doesn't want to take money from.
- **The quality gate on checkout.** Refusing payment from a user whose profile can't produce
  good matches is the intended behavior.
- **Honest testimonials.** The landing page runs under the heading "Review Jujur" (honest
  reviews) and includes a user saying the product helped but the interviews still went
  nowhere. Keep it.
- **The stated ethos**: *don't sell to people who can't afford it*; *empty LinkedIn = bad
  assessments*; *sustainable, not predatory — fewer paying users who get real value beats a
  churn-and-burn funnel*.
- **Bahasa "kamu" verdicts** and the casual, occasionally self-deprecating tone.
- **AGPL and a public repo** as a trust signal: anyone can audit how their data is handled
  or self-host.

---

## 8. Known drift — marketing vs. reality

Recorded as fact, not as a task list. Verify against the code before repeating any of it:

- **The free tier is gone.** `about.md`, `producthunt.md`, the pitch deck, and the landing
  page's stats sub-copy still advertise roughly 20 free assessments after registration. The
  product is now paid-only and the first crawl is triggered by payment. The sign-in
  checklist already tells users the truth.
- **Source count.** Marketing docs name Indeed and JobStreet only. Five sources are
  integrated (§5), and the landing page's source strip lists four of them.
- **Pricing is not on the landing page.** There is no pricing section and no FAQ; plans are
  only visible after signing in.

---

## 9. Related docs

- `CLAUDE.md` — architecture, stack, conventions, commands.
- `docs/payment-mechanism.md` — the billing and subscription flow in full technical detail.
- `about.md` / `README.md` / `producthunt.md` — public-facing narrative (see §8 first).
- `beforeyoubuy.md` — the customer-facing ethos, source of the sign-in checklist.

---

## 10. Vocabulary

| Term | Meaning |
|---|---|
| **Pencarian** | A saved search / job preference. The unit a plan meters. |
| **Loker Tersedia** | The user's match list. "Loker" = lowongan kerja, a job opening. |
| **Penilaian** | An assessment — one job scored against one search. |
| **Paket** | A subscription plan. |
| **Verdict** | The short Bahasa explanation attached to a score. |
| **Skill gap** | Skills the job requires that the candidate's profile lacks. |
| **High-fit** | A match scoring 80 or above. Drives the daily email and public stats. |
| **Open to Work** | LinkedIn flag; unlocks the discount on the cheapest plan. |
