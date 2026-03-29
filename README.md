# ListingJet — Listing Media OS

> From raw listing media to launch-ready marketing in minutes.

ListingJet is an AI-powered real estate listing media platform. Photographers and agents upload raw photos; a 15-agent AI pipeline automatically curates, scores, packages, and delivers MLS-compliant bundles, branded flyers, listing descriptions, social captions, floor plan visualizations, and cinematic video tours — all in one workflow.

[![CI](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/test.yml/badge.svg)](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/test.yml)
[![Lint](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/lint.yml/badge.svg)](https://github.com/jlabella44-cpu/Launchlens/actions/workflows/lint.yml)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Next.js 16 Frontend                          │
│    /listings  /listings/[id]  /billing  /admin  /pricing  /demo      │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ REST / SSE
┌───────────────────────────▼──────────────────────────────────────────┐
│                     FastAPI (Python 3.12)                            │
│  /auth  /listings  /assets  /billing  /admin  /demo  /webhook/sse    │
│  Middleware: JWT decode → RLS tenant isolation                       │
└─────────┬───────────────────────────────────┬────────────────────────┘
          │ SQLAlchemy 2.0 async              │ Temporal SDK
          ▼                                   ▼
┌─────────────────────┐        ┌─────────────────────────────────────┐
│   PostgreSQL 16     │        │         Temporal Workflow           │
│   (RLS enabled)     │        │                                     │
│   10 tables +       │        │  Phase 1: Ingest → Vision → Cover   │
│   credit_transactions│        │           → Package → AWAIT_REVIEW │
└─────────────────────┘        │                    │                 │
                                │             signal: approve         │
┌─────────────────────┐        │                    ▼                 │
│     Redis 7         │        │  Phase 2: Content ──────────────────┤
│  Rate limiting      │        │           ├─ Brand (parallel)       │
│  SSE pub/sub        │        │           └─ Social (Pro+)          │
└─────────────────────┘        │           → MLS Export → Distribute │
                                └─────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│                          AI Providers                                │
│  Google Cloud Vision API  │  OpenAI GPT-4V  │  Anthropic Claude     │
│  Kling AI (video gen)     │  AWS S3 (storage)                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Agent Pipeline (15 agents)

| Agent | Phase | Description |
|-------|-------|-------------|
| IngestionAgent | 1 | Dedup by file hash, upload to S3 |
| VisionAgent | 1 | Google Vision tier-1 bulk + GPT-4V tier-2 top 20 |
| CoverageAgent | 1 | Verify required shot types (exterior, kitchen, etc.) |
| PackagingAgent | 1 | Score + select top 25 photos → AWAITING_REVIEW |
| ContentAgent | 2 | Dual-tone listing descriptions (MLS-safe + marketing) via Claude |
| BrandAgent | 2 | Render branded PDF flyer → S3 |
| SocialContentAgent | 2 | Instagram + Facebook captions via Claude (Pro+) |
| MLSExportAgent | 2 | Dual ZIP bundles: MLS-unbranded + Marketing-branded |
| DistributionAgent | 2 | Final state → DELIVERED, emit pipeline.completed event |
| PhotoComplianceAgent | 2 | Detect compliance issues (signs, people, branding) |
| FloorplanAgent | 2 | GPT-4V floorplan analysis → 3D dollhouse JSON |
| VideoAgent | 2 | Kling AI image-to-video clips → stitched tour |
| ChapterAgent | 2 | GPT-4V keyframe analysis → chapter markers |
| SocialCutAgent | 2 | Platform-specific clips (IG, TikTok, FB, YT Shorts) |
| LearningAgent | 2 | Read override events → update per-tenant photo weights |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic |
| Orchestration | Temporal (durable workflow + activities) |
| Database | PostgreSQL 16 with Row-Level Security |
| Cache / Queue | Redis 7 (rate limiting, SSE pub/sub) |
| Storage | AWS S3 (boto3) |
| Auth | JWT (PyJWT), bcrypt |
| Payments | Stripe (checkout, portal, webhooks) |
| AI Vision | Google Cloud Vision API, OpenAI GPT-4V |
| AI Content | Anthropic Claude 3 |
| AI Video | Kling AI |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| 3D | React Three Fiber, Three.js, Framer Motion |
| Observability | OpenTelemetry (OTLP), CloudWatch metrics, Sentry |
| Testing | pytest-asyncio (270+ tests) |
| CI/CD | GitHub Actions (lint, test, docker build) |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12
- Node.js 20+

### 1. Clone and configure

```bash
git clone https://github.com/jlabella44-cpu/Launchlens.git
cd Launchlens
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and JWT_SECRET
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis temporal temporal-ui
```

### 3. Run migrations

```bash
pip install -e ".[dev]"
python -m alembic upgrade head
```

### 4. Start the API and worker

```bash
# Terminal 1 — API server
uvicorn listingjet.main:app --reload --port 8000

# Terminal 2 — Temporal worker
python -m listingjet.workflows.worker
```

### 5. (Optional) Start the frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

### URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Temporal UI | http://localhost:8233 |
| Frontend | http://localhost:3000 |

### Full stack via Docker Compose

```bash
docker compose up -d
```

---

## Running Tests

```bash
# Spin up test database first
docker compose up -d postgres-test

# Run all tests
python -m pytest --tb=short -q

# Run specific test module
python -m pytest tests/test_api/test_listings.py -v
```

The test suite uses a separate PostgreSQL database on port 5433. See `tests/conftest.py` for fixture setup.

---

## API Documentation

Interactive API docs are available at **http://localhost:8000/docs** when the server is running.

Key endpoints:

```
POST /auth/register          Register new tenant + admin user
POST /auth/login             JWT login
POST /listings               Create listing
POST /listings/{id}/assets   Upload photos → triggers Temporal pipeline
POST /listings/{id}/review   Claim for review (IN_REVIEW)
POST /listings/{id}/approve  Approve → triggers Phase 2 pipeline
GET  /listings/{id}/export   Download MLS or Marketing ZIP bundle
GET  /webhook/sse            Server-sent events stream
POST /billing/checkout       Create Stripe checkout session
POST /billing/webhook        Stripe webhook receiver
GET  /admin/tenants          List all tenants (admin only)
GET  /admin/stats            Platform statistics
GET  /admin/credits/summary  Credit system overview
```

---

## Environment Variables

See [`.env.example`](.env.example) for all configuration options with comments.

---

## Project Structure

```
src/listingjet/
  main.py              FastAPI app factory + lifespan
  config.py            Settings (pydantic-settings, .env)
  database.py          SQLAlchemy engine, sessions, RLS helper
  agents/              15 AI processing agents (BaseAgent pattern)
  activities/          Temporal activity wrappers
  workflows/           Temporal workflow definitions + worker
  api/                 FastAPI routers (auth, listings, billing, admin)
  models/              SQLAlchemy ORM models
  providers/           AI provider abstractions (Vision, LLM, Template)
  services/            Business logic (auth, billing, events, metrics)
  monitoring/          Sentry init, OTel tracing
alembic/versions/      10 database migrations
tests/                 270+ pytest tests
frontend/              Next.js 16 application
docker/                Init scripts, entrypoint
.github/workflows/     CI/CD pipelines
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make changes and add tests
5. Run linting: `ruff check src/ tests/`
6. Run tests: `python -m pytest --tb=short -q`
7. Push and open a pull request

All CI checks (lint, test) must pass before merging.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
