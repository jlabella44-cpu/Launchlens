# ListingJet — Claude Code Session Guide

## What this project is

**ListingJet** is a SaaS platform that automates real estate listing media: agents upload property photos and get back MLS export bundles, AI descriptions, branded flyers, social content, a video tour, and a 3D floorplan — all processed through a 14-agent pipeline run by an in-process worker polling a Postgres job table (`src/listingjet/pipeline/`).

- **Backend:** FastAPI + PostgreSQL (job table) + Redis, Python 3.12, Alembic migrations
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, TypeScript
- **Infra:** Render (API + worker), Supabase Postgres, Upstash Redis, Cloudflare R2 (media) — see `render.yaml`.
- **Tests:** pytest + pytest-cov, vitest for frontend

---

## Branching

Create a **fresh feature branch per task** off `main`. Name it for the work
(`fix/…`, `feat/…`, `docs/…`, `chore/…`). Push, open a PR, do not merge to
`main` without an explicit green light.

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <branch-name>
# …work…
git push -u origin <branch-name>
```

Do **not** push to `main` directly and do **not** amend published commits.
`gh pr create` works on this machine (verified 2026-04-17) — use it
directly. Fallback: the compare URL printed by `git push` also works.

---

## Bash commands

Every `Bash` tool call must pass an explicit `timeout`. The harness default
of 2 minutes will kill long-running commands (`pytest`, `docker build`,
`npm ci`) silently — always set a ceiling that matches the expected
runtime.

---

## Running the project

```bash
# Start all services (postgres, redis, api, worker)
docker-compose up

# Run backend tests
pip install -e ".[dev]"
python -m pytest --tb=short -q

# Run frontend
cd frontend && npm ci && npm run dev

# Run frontend tests
cd frontend && npm run lint && npx vitest run
```

---

## Key file locations

> **Package naming:** the repo directory is `launchlens` and the PostgreSQL DB name is `launchlens`, but the Python package, Docker user, and all branding are `listingjet` (renamed 2026-03-29, commit `4c94d1f`). Anything under `src/launchlens/` or `design-system/launchlens/` is pre-rename cruft and has been removed — do **not** recreate those paths.

### Backend — `src/listingjet/`

| What | Where |
|---|---|
| FastAPI app entry | `main.py` |
| Pipeline worker entry (standalone: `python -m listingjet.pipeline.worker`) | `pipeline/worker.py` |
| Job-table definition + runner | `pipeline/` |
| DB engine / session | `database.py` |
| Logging setup | `logging_config.py` |
| API routers | `api/` |
| Per-route Pydantic schemas | `api/schemas/` |
| Pipeline agents | `agents/` |
| SQLAlchemy models | `models/` |
| Business-logic services | `services/` (auth, billing, credits, email, audit, rate-limit, etc.) |
| AI/media provider adapters | `providers/` (Claude (text + vision), OpenAI images, Kling, Canva); prompt templates under `providers/templates/` |
| FastAPI middleware | `middleware/` |
| Pricing-tier configuration | `config/` (currently `tiers.py`) |
| Observability (Sentry only) | `monitoring/` |
| Email templates (Jinja) | `templates/email/` |
| Utility helpers | `utils/` |
| Shared schemas (stub) | `schemas/` — empty today; active schemas live under `api/schemas/` |

### Backend support

| What | Where |
|---|---|
| Alembic migrations | `alembic/versions/` (001→055, linear) |
| Backend pytest suite | `tests/` |
| Migration / seed / smoke scripts | `scripts/` |

### Frontend — `frontend/src/`

| What | Where |
|---|---|
| App Router pages | `app/` (incl. `admin/`, `analytics/`, `billing/`, `changelog/`, `demo/[id]/`, `faq/`, `review/`, `support/`, `terms/`, `privacy/`, `onboarding/`, `accept-invite/`, `settings/team/`) |
| Components (root) | `components/` |
| shadcn/ui primitives | `components/ui/` |
| Layout components | `components/layout/` |
| Analytics components | `components/analytics/` |
| Notification components | `components/notifications/` |
| Listing creation wizard | `components/listings/creation-wizard/` |
| React context providers | `contexts/` |
| Custom React hooks | `hooks/` |
| Client-side helpers | `lib/` (generated API client under `lib/generated/`) |
| Frontend tests | `__tests__/` |

### Infra & ops

| What | Where |
|---|---|
| Dockerfile + compose | `Dockerfile`, `docker-compose.yml`, `docker/` |
| Design tokens / system | `design-system/listingjet/` |
| Frontend Vercel config | `frontend/vercel.json` |

### Docs & planning

| What | Where |
|---|---|
| Master task list | `MASTER_TODO.md` |
| Other specs, PRDs, handoffs | `docs/` |
| LLM-friendly project overview | `PROJECT_OVERVIEW_FOR_LLM.md` |

---

## Important constraints

- **Never push to `main` directly** — go through the feature branch
- **Never amend published commits** — create new commits
- **Migration head: 055** — next migration must chain off `055_vision_result_analysis`
- **Feature flags** — `FEATURES=` is a comma-separated env list (see `src/listingjet/features.py`) of: `learning`, `health_score`, `performance_intelligence`, `help_agent`, `microsite`, `webhooks`, `listing_permissions`. All off by default. Routers are selected at app start based on this value, so changing `FEATURES` requires restarting the API and worker processes.
- Routes are mounted at their router prefix directly (e.g. `/auth/...`, `/listings/...`, `/demo/...`) — there is no `/v1` prefix in the running app despite past plans. Health endpoints (`/health`, `/health/deep`) are at their literal paths; `/ready` is not implemented.
- The stop hook in `~/.claude/settings.json` will block you from stopping if there are uncommitted changes or unpushed commits — commit and push before ending the session.
