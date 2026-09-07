# ListingJet — Listing Media OS

> From raw listing media to launch-ready marketing in minutes.

ListingJet is an AI-powered real estate listing media platform. Agents and photographers upload raw photos; a 21-step pipeline curates, scores, packages, and delivers MLS-compliant bundles, branded flyers, listing descriptions, social captions, floorplan and 3D dollhouse visualizations, and cinematic video tours in one workflow.

[![CI](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/test.yml/badge.svg)](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/test.yml)

---

## Architecture

```
                 Browser
                    |
        +-----------v------------+
        |  Next.js 16 (Vercel)   |   /api/* rewritten to the Render API
        |  App Router, React 19  |   media served from NEXT_PUBLIC_MEDIA_HOST
        +-----------+------------+
             REST + SSE (/sse/listings/{id}/events)
        +-----------v--------------------------------+
        |  FastAPI on Render (one free web service)  |
        |  API routers + pipeline worker in-process  |
        |  JWT auth -> RLS tenant isolation          |
        +--+--------------+--------------+-----------+
           |              |              |
   +-------v------+ +-----v------+ +-----v------------+
   | Supabase     | | Upstash    | | Cloudflare R2    |
   | Postgres 16  | | Redis      | | media objects    |
   | RLS,         | | rate limit | | S3-compatible    |
   | pipeline_jobs| | revocation | |                  |
   +--------------+ +------------+ +------------------+

   Providers: Anthropic Claude (claude-haiku-4-5 per photo,
   claude-sonnet-5 for copy and floorplan) - OpenAI gpt-image-1.5
   (virtual staging, image edits, dollhouse render) - Runway
   (gen4_turbo interiors, veo3.1_fast exteriors) - Canva (flyers)
   - Resend (email) - Stripe (billing) - Sentry (errors)
```

The worker is not a separate service. `WORKER_ENABLED` (default `true`) starts the polling loop inside the API process at startup; see `lifespan` in `src/listingjet/main.py`.

### Pipeline (21 steps)

Each step is one row in `pipeline_jobs`. A row becomes runnable when every step it needs is done, skipped, or failed-and-optional. The list is declared in `src/listingjet/pipeline/definition.py`.

| Step | Needs | What it does | Gate |
|---|---|---|---|
| `ingestion` | — | Dedupe by file hash, upload originals to R2 | — |
| `photo_analysis` | `ingestion` | One Claude vision call per photo: room type, quality, hero score, compliance | — |
| `property_verification` | `ingestion` | Public property data lookup (ATTOM, Walk Score) | optional |
| `coverage` | `photo_analysis` | Check that the required shot types are present | — |
| `virtual_staging` | `coverage` | Furnish empty rooms with OpenAI image generation | optional, `addon:virtual_staging` |
| `floorplan` | `coverage`, `virtual_staging` | Claude floorplan analysis into a DollhouseScene JSON | — |
| `dollhouse_render` | `floorplan` | Bake the scene into an isometric 3D render | optional |
| `packaging` | `floorplan`, `dollhouse_render`, `property_verification` | Score and select the delivered photo set | — |
| `video_baseline` | `packaging` | Free ffmpeg Ken Burns tour with an end card | optional |
| `video_ai` | `packaging`, `await_review` | Runway clips stitched into a cinematic tour | optional, `addon:ai_video_tour` |
| `await_review` | `packaging` | Human approval gate | `review` |
| `content_social` | `await_review` | Listing copy and social captions in one Claude call | — |
| `brand` | `content_social` | Branded PDF flyer | optional |
| `social_cuts` | `video_baseline`, `video_ai`, `await_review` | Platform-specific vertical clips | optional |
| `mls_export` | `content_social`, `brand` | MLS-unbranded and marketing-branded ZIP bundles | — |
| `distribution` | `mls_export`, `social_cuts` | Mark the listing delivered, emit the completion event | — |
| `microsite` | `distribution` | Single-property landing page plus QR code | optional, `feature:microsite` |
| `learning` | `distribution` | Update per-tenant photo weights from review overrides | optional, `feature:learning` |
| `social_event` | `distribution` | Just-listed listing event and social reminders | optional |
| `health_score` | `distribution` | Composite listing health score | optional, `feature:health_score` |
| `performance_intelligence` | `distribution` | Link photo selections to listing outcomes | optional, `feature:performance_intelligence` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic |
| Orchestration | In-process worker polling the `pipeline_jobs` table (`src/listingjet/pipeline/`) |
| Database | PostgreSQL 16 with Row-Level Security (Supabase in production) |
| Cache | Redis 7 for rate limits and token revocation (Upstash in production) |
| Storage | Cloudflare R2 via the boto3 S3-compatible client |
| Auth | JWT (PyJWT), bcrypt |
| Payments | Stripe (checkout, portal, webhooks) |
| AI vision and copy | Anthropic Claude: `claude-haiku-4-5` per photo, `claude-sonnet-5` for copy and floorplan |
| AI images | OpenAI `gpt-image-1.5` for virtual staging, image edits, and the dollhouse render |
| AI video | Runway: `gen4_turbo` for interiors, `veo3.1_fast` for exteriors, stitched with ffmpeg |
| Templates and email | Canva (flyers), Resend (transactional email) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Observability | Sentry |
| Testing | 900+ pytest, vitest |
| CI/CD | GitHub Actions: test (backend + frontend), docker build |

---

## Quick Start

### Prerequisites

- Python 3.12
- Node.js 22
- PostgreSQL 16, local or via `docker-compose up postgres`
- ffmpeg on PATH (used by `video_baseline` and `social_cuts`)

### 1. Clone and configure

```bash
git clone https://github.com/jlabella44-cpu/Launchlens.git
cd Launchlens
cp .env.example .env
```

At a minimum set:

```bash
DATABASE_URL=postgresql+asyncpg://listingjet:password@localhost:5432/launchlens
DATABASE_URL_SYNC=postgresql://listingjet:password@localhost:5432/launchlens
JWT_SECRET=<32 or more random characters>
REDIS_URL=redis://localhost:6379/0
USE_MOCK_PROVIDERS=true
FFMPEG_BIN=ffmpeg
```

`USE_MOCK_PROVIDERS=true` swaps every AI provider for `src/listingjet/providers/mock.py`, so the pipeline runs end to end with no API keys and no spend. Redis is optional for a first run: the app logs a warning at startup and degrades rate limiting if it cannot connect.

`.env.example` is generated from `Settings`. Run `just env-example` to regenerate it; never edit it by hand.

### 2. Migrate and run

```bash
pip install -e ".[dev]"
alembic upgrade head
just dev        # uvicorn listingjet.main:app --reload --port 8000
```

The pipeline worker starts inside the API process. Run it separately only if you set `WORKER_ENABLED=false`:

```bash
just worker     # python -m listingjet.pipeline.worker
```

### 3. Frontend

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# http://localhost:3000
```

`NEXT_PUBLIC_MEDIA_HOST` is required for a production build (`next build`) and optional in dev.

### Everything at once with Docker

```bash
docker-compose up
```

### URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API docs (Swagger, non-production only) | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |

---

## Running Tests

The suite talks to a separate Postgres on port 5433 (see `TEST_DB_URL` in `tests/conftest.py`).

```bash
docker-compose up postgres-test   # or point 5433 at a local cluster
just test                         # pytest -q, the full suite
just check                        # ruff plus the non-DB, non-ffmpeg subset (fast)
```

Frontend:

```bash
cd frontend
npm run lint && npx tsc --noEmit && npx vitest run
```

---

## API Documentation

Interactive docs are at http://localhost:8000/docs whenever the server runs outside production. Routers mount at their own prefix; there is no `/v1`.

```
POST /auth/register            Register a tenant and admin user
POST /auth/login               JWT login
POST /listings                 Create a listing
POST /listings/{id}/assets     Upload photos, enqueue the pipeline
POST /listings/{id}/approve    Approve, releasing the post-review steps
GET  /listings/{id}/export     Download the MLS or marketing ZIP bundle
GET  /sse/listings/{id}/events Server-sent pipeline events (?token=<jwt>)
POST /billing/checkout         Create a Stripe checkout session
POST /billing/webhook          Stripe webhook receiver
GET  /admin/tenants            List tenants (admin only)
GET  /health, /health/deep     Liveness, and DB + Redis + worker tick
```

---

## Environment Variables

See [`.env.example`](.env.example) for every setting with comments. Production values, and where each one comes from, are in the [free-tier setup runbook](docs/runbooks/free-tier-setup.md).

---

## Project Structure

```
src/listingjet/
  main.py              FastAPI app factory, router mounts, lifespan
  config/              Settings, ai_rates.py (AI price table), tiers.py (credits)
  database.py          SQLAlchemy engine, sessions, RLS helper
  features.py          FEATURES flag parsing
  agents/              One class per pipeline step
  pipeline/            definition.py (the 21 steps), runner.py, steps.py, worker.py
  api/                 FastAPI routers (auth, listings, billing, admin, sse, ...)
  models/              SQLAlchemy ORM models
  providers/           Claude, OpenAI images, Runway, Canva, and mock adapters
  services/            Auth, billing, credits, email, audit, rate limiting
  monitoring/          Sentry init
alembic/versions/      Migrations, 001 to 056, linear
tests/                 pytest suite
scripts/               Seed, smoke, env-example generation, doc link check
frontend/              Next.js 16 application
docker/                Init scripts, entrypoint
.github/workflows/     test.yml, deploy.yml, docker.yml
```

---

## Deployment

Production runs entirely on free tiers: Render (API plus in-process worker), Supabase (Postgres), Upstash (Redis), Cloudflare R2 (media), and Vercel (frontend). The blueprint is [`render.yaml`](render.yaml) and the full provisioning walkthrough is the [free-tier setup runbook](docs/runbooks/free-tier-setup.md). Pushing to `main` triggers `deploy.yml`, which calls the Render deploy hook; Render's `preDeployCommand` runs the Alembic migrations and aborts the deploy if they fail.

---

## Contributing

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Make changes and add tests
4. Backend gates: `just check`, then `just test`
5. Frontend gates: `npm run lint && npx tsc --noEmit && npx vitest run`
6. Push and open a pull request

All CI checks must pass before merging.

---

## License

MIT License. (There is no `LICENSE` file in the repository yet.)
