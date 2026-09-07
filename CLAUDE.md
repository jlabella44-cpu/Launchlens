# ListingJet — Claude Code Session Guide

## What this project is

**ListingJet** is a SaaS platform that automates real estate listing media: agents upload property photos and get back MLS export bundles, AI descriptions, branded flyers, social content, a video tour, and a 3D floorplan — all processed through a 14-agent pipeline run by an in-process worker polling a Postgres job table (`src/listingjet/pipeline/`).

- **Backend:** FastAPI + PostgreSQL (job table) + Redis, Python 3.12, Alembic migrations
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, TypeScript
- **Infra:** Render (single free-tier web service; the worker runs in-process via `WORKER_ENABLED`, not a separate Render service), Supabase Postgres, Upstash Redis, Cloudflare R2 (media) — see `render.yaml`.
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

A `justfile` at the repo root wraps the common commands. On Windows (no
POSIX `just` runtime), call the `.venv/Scripts/*` binaries directly instead
of `just <target>`:

```bash
just check       # ruff check src tests alembic + pytest -m "not db and not ffmpeg" -q
just test        # pytest -q (full suite)
just dev          # uvicorn listingjet.main:app --reload --port 8000
just worker       # python -m listingjet.pipeline.worker
just env-check    # scripts/gen_env_example.py --check (fails if .env.example is stale)

# Windows equivalents (no `just` runtime):
.venv/Scripts/ruff.exe check src tests alembic
.venv/Scripts/pytest.exe -m "not db and not ffmpeg" -q
.venv/Scripts/python.exe -m uvicorn listingjet.main:app --reload --port 8000
.venv/Scripts/python.exe -m listingjet.pipeline.worker
.venv/Scripts/python.exe scripts/gen_env_example.py --check
```

```bash
# Start all services (postgres, redis, api — worker runs in-process via
# WORKER_ENABLED=true, already set for the api service in docker-compose.yml)
docker-compose up

# Run backend tests
pip install -e ".[dev]"
python -m pytest --tb=short -q

# Run frontend
cd frontend && npm ci && npm run dev

# Run frontend tests
cd frontend && npm run lint && npx vitest run
```

`.env.example` is **generated** — `scripts/gen_env_example.py` derives it
from `Settings.model_fields`; never hand-edit it. Regenerate with
`scripts/gen_env_example.py` (no flag) after adding/removing a setting, and
run `--check` to verify it's current — `test.yml`'s `backend` job runs
`python scripts/gen_env_example.py --check` as a hard gate, so a stale
`.env.example` fails CI.

---

## CI

One workflow, `.github/workflows/test.yml` ("Test"), runs on every PR and
on push to `main`: a `backend` job (Postgres test DB on 5433 + Redis
services, Alembic migrations, ffmpeg, `ruff check src tests alembic
scripts`, the `.env.example` drift check, `pytest`) and a `frontend` job (`npm ci`,
lint, `tsc --noEmit`, `vitest run`, `npm run build`). `deploy.yml` triggers
the Render deploy hook only on push to `main` (API service only — the
worker runs in-process inside that same service via `WORKER_ENABLED`, so
there's no separate worker deploy). `docker.yml` builds the Docker image
(no push) on every PR and on push to `main`, to catch Dockerfile breakage
before merge. `lint.yml` was removed — Ruff now runs inside `test.yml`'s
`backend` job.

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
| AI/media provider adapters | `providers/` (Claude (text + vision), OpenAI images, Runway video, Canva) |
| FastAPI middleware | `middleware/` |
| Pricing-tier configuration | `config/` (currently `tiers.py`) |
| Observability (Sentry only) | `monitoring/` |
| Email templates (Jinja) | `templates/email/` |
| Utility helpers | `utils/` |
| Shared schemas (stub) | `schemas/` — empty today; active schemas live under `api/schemas/` |

### Backend support

| What | Where |
|---|---|
| Alembic migrations | `alembic/versions/` (001→056, linear) |
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
- **Migration head: 056** — next migration must chain off `056_video_asset_metadata`
- **Feature flags** — `FEATURES=` is a comma-separated env list (see `src/listingjet/features.py`) of: `learning`, `health_score`, `performance_intelligence`, `help_agent`, `microsite`, `webhooks`, `listing_permissions`. All off by default. Routers are selected at app start based on this value, so changing `FEATURES` requires restarting the API and worker processes.
- Routes are mounted at their router prefix directly (e.g. `/auth/...`, `/listings/...`, `/demo/...`) — there is no `/v1` prefix in the running app despite past plans. Health endpoints (`/health`, `/health/deep`) are at their literal paths; `/ready` is not implemented. **Exception:** the SSE pipeline-events stream in `api/sse.py` is mounted at `/sse` (`GET /sse/listings/{id}/events`), not under `/listings`, because `api/listing_events.py` already owns `GET /listings/{id}/events` for an unrelated feature (social-reminder events). Frontend code must build the SSE URL with the `/sse` prefix.
- The stop hook in `~/.claude/settings.json` will block you from stopping if there are uncommitted changes or unpushed commits — commit and push before ending the session.
