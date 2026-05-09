# cariinkerja.id

Asisten cari kerja yang nilai tiap lowongan buat kamu — biar ga buang waktu apply ratusan posisi yang ga fit.

## Masalah

Cari kerja di Indonesia itu melelahkan. Buka Indeed, buka JobStreet, scroll ratusan lowongan, baca JD panjang, terus apply ke semuanya sambil berharap. Padahal mayoritas posisi itu ga cocok sama skill atau preferensi kamu — cuma kebuang waktu di kedua sisi.

## Cara kerja

1. **Set profil + preferensi.** Sambungin LinkedIn, isi tipe kerjaan yang kamu mau (title, remote/onsite, sumber).
2. **Bot kerja buat kamu.** Crawler kami pantau Indeed & JobStreet sesuai preferensi, ambil lowongan baru tiap hari.
3. **AI nilai tiap lowongan.** Tiap posting di-assess pake LLM: skor kecocokan 0-100, daftar skill yang match, skill yang masih kurang, plus verdict singkat kenapa cocok atau engga.
4. **Kamu tinggal lihat yang skornya tinggi.** Fokus apply ke 5-10 lowongan yang beneran fit, bukan 200 yang random.

## Untuk siapa

- **Fresh graduate** yang bingung dari mana mulai dan mana yang realistis dilamar.
- **Career switcher** yang butuh peta skill gap sebelum lompat industri.
- **Kandidat sibuk** yang ga sempet screening manual tiap hari.

## Status

Udah live di [cariinkerja.id](https://cariinkerja.id) — dipake paying users tiap hari. Daftar terbuka untuk umum.

Sebelum beli, baca dulu [Before You Buy](beforeyoubuy.md).

---

## Development

Open source under [AGPL-3.0-or-later](LICENSE).

### Stack

Django 5.2 + DRF backend, Vite + React 19 + TanStack Router/Query SPA frontend, Postgres (SQLite fallback for dev), Celery + Redis for async crawls and LLM-based assessment, Tailwind v4. Uses Apify for LinkedIn ingest, OpenAI for scoring, Mayar for payments, and Google OAuth for sign-in.

See [CLAUDE.md](CLAUDE.md) for the full architecture overview.

### Prerequisites

- Python ≥3.10 with [uv](https://docs.astral.sh/uv/)
- Node ≥20 with [pnpm](https://pnpm.io/)
- Redis (for Celery broker)
- Postgres (optional — SQLite is the host-dev fallback)
- Docker + Docker Compose (optional — for the containerized path)

### Local setup

```sh
# 1. Configure env
cp .env.example .env
cp frontend/.env.example frontend/.env
# Fill in OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, etc.

# 2. Install backend deps + run migrations
uv sync
make migrate

# 3. Start services (each in its own terminal)
make dev      # Django on http://localhost:8000
make web      # Vite SPA on http://localhost:5173
make worker   # Celery worker
make beat     # Celery beat (DB-backed scheduler)
```

`.env.example` is the source of truth for required environment variables. Empty values disable optional integrations (Discord, email, Mayar) gracefully.

### Docker path

```sh
cp .env.example .env.docker   # set POSTGRES_HOST=postgres for compose
make dock                     # build + up + tail logs
```

### Tests

```sh
uv run manage.py test                    # full suite
uv run manage.py test assessment         # one app
make lint                                # ruff format + check
```

### Contributing

Issues and PRs welcome. Please run `make lint` before opening a PR. Security disclosures: see [SECURITY.md](SECURITY.md).
