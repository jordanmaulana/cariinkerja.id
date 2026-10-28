# Brand & Voice — cariinkerja.id

*Last verified: 2026-10-22.* How the brand looks, how it talks, and the copy that already
exists. Quotes are **verbatim**; each one names its source file so it can be re-checked.

---

## 1. Visual identity

### Logo mark: the "92" score ring
- A rounded square with a dark gradient, containing a purple ring arc filled ~92% around a white "92".
- Reads as "a high match score". The logo *is* the product's core output.
- Sources:
  - `frontend/src/components/brand/logo-mark.tsx` (component)
  - `frontend/public/favicon.svg` (adds a small "/ 100" and a purple four-point sparkle)
  - `assets/launch/cariinkerja-icon.svg` + `-240.png` (Product Hunt icon)
  - `frontend/public/icon-192.png`, `icon-512.png`, `apple-touch-icon.png`
- **Lockup:** logo mark + the wordmark "cariinkerja" with ".id" at 60% opacity.
- **Spelling:** always lowercase **cariinkerja.id** in copy. (Older `producthunt.md` uses "Cariinkerja".)

### Colours

| Token | Value | Use |
|---|---|---|
| Brand purple | `#863bff` | Logo arc, score gauges in brand graphics, accents. Also the PWA `theme_color`. |
| Dark gradient | `#1a1424` → `#050308` | Logo tile, OG image, video backgrounds |
| Card | `oklch(0.205 0 0)` | Dark cards in graphics |
| Match green | Tailwind emerald-400 | ✓ matched skill chips |
| Gap red | `oklch(0.704 0.191 22.216)` | ✗ missing skill chips |

The **app UI itself is neutral** (default shadcn black/white, light and dark themes).
Purple belongs on brand surfaces: logo, OG image, social graphics, video.

### Typography
- **Geist** (variable) everywhere: app and video. The logo's "92" is Helvetica Neue, weight 800.

### Social video tokens
- `ads/remotion/src/brand.tsx` holds the ready-made building blocks: Background, LogoMark (animated arc), Lockup, ScoreGauge, Chip, Card, Eyebrow.
- Format: **1080×1920 (9:16), 30 fps, Geist**. Reuse these instead of inventing new styling.

### Off-brand: don't copy
`_docs/pitch/pitch-deck.html` uses Fraunces / Hanken Grotesk and emerald `#34d399` on near-black. That was an investor-deck one-off, not the brand.

---

## 2. Open Graph image

File: [og-image.png](og-image.png), 1200×630. It is a copy of `frontend/public/og-image.png`.
The live URL is `https://cariinkerja.id/og-image.png?v=2`.

**What's on it:** a dark purple-glow background. Top: the "92" logo + "cariinkerja.id". Headline: **"Cariin kamu loker yang cocok,"** (white) / **"biar kamu ga capek cari sendiri."** (grey). Below that, a mock assessment card: **87** score ring, "Frontend Engineer", "Tokopedia · Jakarta", chips ✓ React ✓ TypeScript ✓ Tailwind ✗ GraphQL.

**Link-preview meta** (`frontend/index.html`, verbatim):
- Title: `cariinkerja.id — Cariin kamu loker yang cocok`
- Description: `Tiap hari kita cek loker baru yang cocok sama profilmu, dan tunjukin skill apa yang kurang dari kamu.`
- Image alt: `cariinkerja.id — skor kecocokan loker 87/100 plus skill yang masih kurang`
- `og:locale` `id_ID`; `twitter:card` `summary_large_image`.

**No source file exists.** The PNG was committed as a binary (commit `94ba841`, 2026-09-27).
To change it, design a new 1200×630 PNG. Then:
1. Replace `frontend/public/og-image.png`.
2. Bump `?v=` in both `og:image` and `twitter:image` in `frontend/index.html`.
3. Re-copy the PNG into this folder.

---

## 3. Voice & tone

The brand speaks like **Jordan, the founder**, talking to a friend who's job hunting. Condensed
from `ads/voice-profile.md`, which analysed ~11 minutes of his videos.

- **Pronouns:**
  - **"aku"** for himself; never "gue" or "saya".
  - **"kamu"** for the reader or viewer, and **"kita"** when it's "us together".
  - **"teman-teman"** is his signature address in longer formats; skip it in short ones.
- **Particles:**
  - **"Jadi…"** opens an explanation.
  - **"Nah,"** turns to the point.
  - End statements and CTAs softly with **"…ya"**.
  - Occasional "kan", "gitu", "sih".
- **English mixing (~9%):** only job and tech terms, never translated, and given Indonesian suffixes: *apply, skill gap-nya, CV-mu, assessment, upgrade skill, apply-apply aja*.
- **Rhetorical moves:**
  - Ask the question, then answer it ("Artinya apa? …").
  - Use **concrete numbers** ("200 loker", "skor 80 ke atas", "lima loker").
  - Tell the reader what to do.
  - Hook with a question.
- **Register:** casual, warm, honest, a little self-deprecating. **Not** corporate SaaS, **not** hype, **not** guru motivational. Admits limits openly; see the honest testimonial in §6.
- **Product verdict voice:** the in-app verdict is always casual Bahasa with "kamu". Mock verdicts in graphics should sound like: *"Cocok banget. Stack React + TS-mu nyambung. Sentuh GraphQL dikit lagi udah aman."*
- **Video pace:** ~5–6 syllables/s; ~130 syllables fit a 30 s spot.

---

## 4. Vocabulary

| Use | Meaning |
|---|---|
| **loker** | job opening (lowongan kerja). The default word, never "lowongan pekerjaan". |
| **skor kecocokan / skor 0–100** | the match score |
| **skill gap** | skills the job needs that the profile lacks |
| **Pencarian** | a saved search; the unit a plan meters ("1 job title" in casual talk) |
| **Loker Tersedia** | the user's match list (menu name) |
| **Penilaian** | an assessment |
| **Paket** | a plan |
| **high-fit / skor 80+** | "Highly Suitable Jobs": drives the daily email and public stats |

More in [product.md §10](product.md#10-vocabulary).

---

## 5. Copy bank (verbatim)

### Landing page (`frontend/src/features/landing/components/`)
- **Hero badge:** "Pencocokan loker bertenaga AI"
- **Hero H1:** "Cariin kamu loker yang cocok, biar kamu ga capek cari sendiri."
- **Hero sub:** "Set preferensimu sekali. Tiap hari kami ambilin loker baru, AI nilai kecocokannya, dan tunjukin skill apa yang masih kurang."
- **CTAs:** "Mulai sekarang" · "Lihat fitur"
- **Microcopy:** "Sign in pake Google. Akun otomatis dibuat — ga perlu daftar manual."
- **Stats section:** "Bukan janji, ini progresnya" / "Udah jalan, datanya nyata." (⚠ its sub-line promises ~20 free assessments; that's stale, don't reuse it)
- **Features section:** "Yang kamu dapet kalo pake cariinkerja.id" / "Empat hal yang ngebantu kamu cari kerja tanpa burnout."
  1. **Preferensi:** "Atur preferensimu sekali, kerjain pencariannya buat kamu." / "Set role, full-time atau freelance, remote atau on-site. Crawler tiap hari ngambilin loker baru sesuai filtermu."
  2. **Skor kecocokan:** "AI ngasih skor 0–100 buat tiap loker, biar kamu ga nebak-nebak." / "Profil + preferensimu dibanding deskripsi loker pake LLM. Hasilnya skor, plus penjelasan singkat kenapa cocok atau nggak."
  3. **Skill gap:** "Tau persis skill apa yang masih kurang per loker." / "Bukan cuma skor — kamu liat hard skill & soft skill mana yang nyambung dan mana yang masih bolong. Bahan upgrade-an yang konkret."
  4. **Statistik:** "Pantau aktivitas pencarianmu, biar tau kapan harus istirahat." / "Berapa loker yang udah dinilai, rata-rata skor, momentum mingguan. Buat refleksi, bukan flexing."
- **Bottom CTA:** "Udah cukup capek scroll loker manual?" / "Sign in sekali, set preferensi, terus biarin AI yang nyari. Kamu fokus aja ke skill upgrade."
- **Footer:** "Dibuat untuk pencari kerja Indonesia."

### Login page (`frontend/src/features/auth/`)
- **Side panel:** "Manfaatin waktu luangmu buat upgrade skill yang kamu butuhin dari loker yang kamu pilih / yaudah terserah mau tidur kek apalah."
- **Feature lines:**
  - "Biar kamu ga omong doang apply banyak loker padahal cuma 3. Atau kalo kamu beneran apply banyak, kamu biar tau kamu layak istirahat sebentar."
  - "Per loker kamu bakal bisa tau skill apa aja yang kamu kurang, biar kamu bisa upgrade skill itu."
- **"Sebelum kamu beli"**: four checkboxes that must all be ticked before Google sign-in unlocks (`consts.ts` `BEFORE_YOU_BUY`):
  1. "Pastiin LinkedIn-mu nggak kopong. Jangan cuma nulis education / job experience cuma title doang."
  2. "Lengkapi apapun yang bisa dilengkapi di LinkedIn-mu. Tulis semua skills, tulis About yang jujur."
  3. "Jangan daftar kalo kamu masih financially struggling. Pastiin energimu buat kamu cari kerja dulu sendiri sampe kamu bisa nafas lega."
  4. "Ini layanan berbayar lho ga pake trial."
- **Checkout lock while a search is still being prepared:** "Sabar, kami lagi ngumpulin loker, nanti muncul di menu Loker Tersedia. Jadi biar kamu tau hasilnya dulu, baru beli. Ok?"

### 30-second ad, "stop spray-and-pray" (`ads/script.md`)
1. "Udah apply 200 loker, yang bales? Nol."
2. "Masalahnya bukan kamu kurang usaha. Tapi lokernya emang dari awal nggak cocok sama profil kamu."
3. "Makanya aku bikin cariinkerja.id."
4. "Jadi kamu cukup set preferensi sekali. Tiap pagi, AI ngecek loker baru, kasih skor 0 sampai 100, plus skill gap-nya."
5. "Nah, ga perlu apply ke ratusan loker random lagi. Fokus aja ke lima loker yang beneran cocok."
6. "Cek cariinkerja.id ya." End card: "Skor 0–100 + skill gap buat tiap loker, tiap hari." + "Mulai sekarang →"

### English taglines (`producthunt.md`, `about.md`, pitch deck)
- "AI scores every job 0–100 so you stop applying blind." *(primary)*
- "Daily AI job matches with skill gaps, in Bahasa."
- "Cariin your fit. AI scores jobs so you don't spray."
- "Not a match flag — a decision tool."
- "Job hunting in Indonesia still feels like 2010."
- "There has to be a better signal than 'I applied to everything.'"
- "A score of 72 with two fixable skill gaps is often a better lead than an 85 you'll never get a callback from."
- "Empty LinkedIn = bad assessments. Garbage in, garbage out."
- "Sustainable, not predatory."
- "If you're hunting hard, you shouldn't be paying full price." *(tied to the dormant Open-to-Work discount; don't use for now)*

### Founder signature lines (from Jordan's past videos)
- "Iya, ekonomi lagi sulit, tapi usahamu jangan ikut sempit."
- "Kamu gak scrolling manual. Kamu tinggal apply aja yang skornya tinggi."
- "Kita bisa sibuk upgrade skill aja yang tertera di skill gap."
- "Validasi itu gak ada ujungnya." *(why there's no trial)*
- "Asik kan? Menurutku ini asik."

---

## 6. Testimonials

Verbatim, shown on the landing page under "Review Jujur" / "Kata pengguna beneran."

Only names and photos are shown, no job titles. Photos are in `frontend/src/assets/`.

- **Nurlianto Aldi** (`testimonial-nurlianto-aldi.jpg`):
  > "Secara overall, cariinkerja.id cukup ngebantu, Mas. Terutama dalam hal mempersingkat waktu dalam pencarian kerja yang cocok. Apalagi udah ada feedback kecocokan antara loker dan CV yang kita punya. Fitur filter nya juga ngebantu, saya biasa pake filter yang dimana skor CV saya berada di atas 75."
- **Rama Widi** (`testimonial-rama-widi.jpg`, written in Javanese):
  > "Iyo sangat membantu jo. Cmn oleh interview2 iki sek syedih. Cmn balasan email tok maksimal. Terus wes gak ono lanjutan e wkwkwkwk"
  >
  > *(Roughly: "Yeah, really helpful. It's just the interviews that are still sad — at most an email reply, then nothing after, lol.")*

**Keep the honest one.** Rama's quote admits the product didn't land him a job. Showing it is
deliberate; it's the brand's credibility. Never edit testimonials or invent new ones.
