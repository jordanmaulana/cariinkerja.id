# Marketing Playbook — cariinkerja.id

*Last verified: 2026-10-22.* What to say, to whom, with what proof, through which channel,
and what never to say. For facts see [product.md](product.md); for wording see
[brand-voice.md](brand-voice.md).

---

## 1. Audiences

| Audience | Pain | Hook that fits |
|---|---|---|
| **Fresh graduates** | Don't know where to start or what's realistically within reach; apply everywhere, hear nothing. | "Udah apply 200 loker, yang bales? Nol." A calibrated score tells them what's in reach. |
| **Career switchers** | Unsure which skills block the jump; afraid of wasting months. | The **skill gap** list per job gives them a concrete learning map before they commit. |
| **Busy candidates** (employed, freelancing, studying) | No time to screen 200 postings a week. | "Set preferensi sekali, tiap pagi udah dinilai." The product does the screening; they just apply. |

**Who we don't target:** people who are financially struggling. The product tells them, in
writing, not to buy yet (sign-in checkbox #3). Never aim ads or copy at desperation
("lagi butuh duit?", "nganggur berbulan-bulan?"). See [Guardrails](#7-guardrails).

---

## 2. Core messages

1. **Stop spray-and-pray.** Apply to the ~5 jobs that fit, not 200 random ones.
2. **A number and a reason, not a yes/no.** A 0–100 score + skill gap + plain-Bahasa verdict for every job.
3. **The gap is the gold.** A 72 with two closable gaps often beats an 85 you'll never get a callback from. Spend the saved time upgrading those skills.
4. **It works while you sleep.** Crawl at 05:00 WIB, email at 09:00 WIB when there's an 80+ match.
5. **Indonesia-first.** Bahasa, "kamu" verdicts, IDR pricing, Indonesian payment, built by an Indonesian solo dev.
6. **Honest by design.** No trial, a quality gate on checkout, an honest testimonial. "Sustainable, not predatory."
7. **Open source.** AGPL, public repo: anyone can audit how their data is handled.

---

## 3. Content pillars

These grow out of formats Jordan has already made and that match his voice. Each pillar has a
proven example (transcripts are in `ads/voice/*.transcript.json`, gitignored, local only).

| Pillar | What it is | Existing example / angle |
|---|---|---|
| **Objection handling** | Answer one real objection per post. | *GADA TRIAL*: there used to be a 1-day trial, but people typed job titles like "Coba kerja" and pasted other people's LinkedIn links. "Validasi itu gak ada ujungnya… Langsung tembokin payment aja." Next ideas: "kenapa harus LinkedIn?", "kenapa skor gue rendah?", "kenapa ga bisa downgrade?" |
| **Stats report** | Dry, mock-official read-out of platform numbers. | *statistik-cariinkerja*: "seolah-olah ini programnya pemerintah". Lead stat: "Di antara 9 loker… hanya ada 2 yang sebenarnya cocok." Always date the numbers. |
| **Job-hunt advice** | Useful advice that isn't a product pitch. | *cuma apply loker*: build an online presence so more people than HR know you exist. "Iya, ekonomi lagi sulit, tapi usahamu jangan ikut sempit." |
| **Product demo** | Screen walkthrough of a real score + gap + verdict. | *cariinkerja_short*: "Asik kan? Menurutku ini asik." "Kita bisa sibuk upgrade skill aja yang tertera di skill gap." |
| **Build in public / origin** | The solo-dev story. | It started as a script that auto-filled a Google Sheet, then became the product. Also: crawler fights, shipping notes, and the AGPL repo. |
| **Honest reviews** | User voice, unpolished. | Both testimonials, especially Rama's ("…interview2 iki sek syedih"). Pair it with "the tool finds the fit; the interview is still on you." |

Formats that already exist: 9:16 talking-head shorts (Jordan on camera, jump cuts), screen
recordings, and one 30 s produced ad.

---

## 4. Proof points

**Traction snapshots: always quote them with their date.**

| Date | Profiles | Jobs crawled | Assessments | High-fit (80+) | Source |
|---|---|---|---|---|---|
| 2026-05-17 | 460 | 2.886 | 9.407 | 1.908 | *statistik* video |
| 2026-06-01 | 615 | 4.118 | 13.660 | 2.649 | `_docs/current-stats.md`, pitch deck |

What can be derived from these: **about 1 in 5 assessed jobs scores 80+** (2.649 / 13.660),
and **"from 9 jobs, only 2 truly fit"** (the 17 May framing).

**Fresh numbers:** `GET https://cariinkerja.id/api/v1/landing/stats/` (public, cached 60 s)
returns `profiles`, `jobs`, `assessments`, `highly_suitable` (score ≥ 80), each with `total`
and `today`. The landing page shows the same live numbers.

**Other proof:** two named testimonials ([brand-voice.md §6](brand-voice.md#6-testimonials)), a public AGPL repo, and live in production since at least mid-May 2026 (460 registrations by 17 May).

---

## 5. Assets

| Asset | Path | Notes |
|---|---|---|
| Open Graph image | [og-image.png](og-image.png) | 1200×630; also works as a generic promo card. |
| Logo / icons | `frontend/public/favicon.svg`, `icon-512.png`, `assets/launch/cariinkerja-icon.svg` | "92" score ring |
| Testimonial photos | `frontend/src/assets/testimonial-*.jpg` | Use only with their exact quotes. |
| 30 s ad | `ads/remotion/out/cariinkerja-ad.mp4` (+ `out/stills/`) | 9:16, rendered **silent**. Jordan records the voice-over himself. The cloned-voice guide track (`remotion/public/vo.wav`) must **never** ship (CC-BY-NC weights). |
| Video template | `ads/remotion/` | Scenes: Hook, Pain, Turn, How, Payoff, CTA, plus brand components. Re-skin it for new scripts. See `ads/README.md`. |
| Founder voice analysis | `ads/voice-profile.md` | Rules for writing scripts in Jordan's voice. |
| Pitch deck | `_docs/pitch/pitch-deck.html` / `.pdf` | Investor-facing, June 2026. Off-brand styling and stale pricing/sources. Mine it for narrative only. |
| Raw founder videos | `/Volumes/ssd/videos` (outside the repo) | Source footage for cut-downs. |
| Product Hunt kit | `producthunt.md`, `assets/launch/` | Taglines are reusable; the description and pricing are stale (§8). |

---

## 6. Channels

- **There are no brand accounts yet** on Instagram, TikTok, X, Threads or YouTube. Creating handles is an open decision for the founder.
- **Existing presence:**
  - Jordan's personal LinkedIn: https://www.linkedin.com/in/jordan-maulana/
  - The GitHub repo: https://github.com/jordanmaulana/cariinkerja.id
  - Jordan's own short videos.
- **Link previews:** OG and Twitter tags are set up, so any post linking `https://cariinkerja.id` renders the OG card on Facebook, LinkedIn, Threads, X and WhatsApp.
- **Every CTA points to** `https://cariinkerja.id` → "Mulai sekarang" → Google sign-in. There's no separate pricing page to link to.
- **Product Hunt:** copy is drafted (`producthunt.md`) but must be corrected first (§8).

---

## 7. Guardrails

Hard rules. Breaking one makes the post wrong or off-brand.

**Truthfulness**
- Never say **gratis / free / trial / coba gratis / coba dulu**. The product is paid-only.
- Quote prices only from [product.md §6](product.md#6-business-model) (Rp 49.000 → 1 search, Rp 99.000 → 3 searches, 30 days).
- Open-to-Work discount is OK to promote: "Open to Work" on LinkedIn → 1-search plan Rp 34.000 (normally Rp 49.000). Only the cheapest plan; upgrades are full price.
- Name only live job sources (Indeed, JobStreet, LinkedIn). **Don't announce Kalibrr/Kitalulus** until `migrate-portal` merges. Safest wording: "dari berbagai job board".
- Never name the AI model. Say "AI".
- Every traction number carries its date.
- **Never promise jobs, interviews, callbacks or hiring speed.** The product finds fit; the user still has to land the interview.

**Ethos** (see [product.md §7](product.md#7-product-constraints-not-to-optimize-away))
- Don't target or exploit desperation. The brand openly tells struggling people *not* to buy yet.
- Keep the honest framing; no hype ("100% dapet kerja!", "rahasia HRD!").
- Don't hide the no-trial rule or the profile-quality requirement. Say them proudly: they filter for the right users.
- Keep testimonials verbatim and never invent them.

**Voice & visuals**
- Casual Bahasa: "aku" / "kamu", never "gue" / "saya" / "Anda". Job/tech terms stay English ([brand-voice.md §3](brand-voice.md#3-voice--tone)).
- No real employer names in **new** mock graphics; use generic ones ("Startup fintech · Jakarta"). The existing OG image's Tokopedia mock is a legacy exception.
- Use the brand tokens (purple `#863bff`, dark gradient, Geist), not the pitch deck's look.

---

## 8. Known gaps & stale claims elsewhere

### Gaps to close before running paid ads (`todo.md`)
- No privacy policy, terms & conditions, or cookie banner. Ad platforms (Meta, Google, TikTok) typically require a privacy-policy URL.
- No pricing section or FAQ on the landing page.
- No sticky mobile CTA.

### Stale claims (don't repeat them; fix the source when convenient)

| Where | Stale claim | Truth |
|---|---|---|
| **Live landing page** `landing-stats.tsx` | "Cari & kasih skor sekitar 20 loker setelah registrasi" | Paid-only. Nothing is crawled before payment. |
| `about.md` | Free tier ("get your footing first"); Indeed + JobStreet only; user picks a source; GPT-4o; full-time vs freelance only | Paid-only; 4 live sources, auto fan-out; no model name; job types are full-time / part-time / contract / internship, remote options are remote / on-site / hybrid |
| `producthunt.md` | Free tier ~20 assessments; "crawls Indeed + JobStreet"; GPT-4o; struggling-user warning "on the landing page" | Paid-only; 4 sources; no model name; the warning lives in the sign-in checklist |
| `README.md` (repo root) | Crawler watches "Indeed & JobStreet" | 4 live sources |
| `_docs/pitch/pitch-deck.*` | "Prove the signal free", Rp 0 tier; source names; old prices | Paid-only; current prices in product.md §6 |
| `beforeyoubuy.md` | 3 items, "Jangan beli…" | The app shows 4 items (adds "Ini layanan berbayar lho ga pake trial."), worded "Jangan daftar…" |
| Older videos (*GADA TRIAL*, *cariinkerja_short*) | Name Indeed / JobStreet; "belasan user" | Still OK as dated content; don't re-cut them as current claims |
