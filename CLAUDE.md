# ListingJet — agent guide

ListingJet turns raw property photos into MLS bundles, branded flyers, listing copy, social captions, a video tour, and a 3D dollhouse render. The work is a 21-step pipeline declared in `src/listingjet/pipeline/definition.py`: enqueueing a listing inserts one `pipeline_jobs` row per step, and a worker running in-process inside the API polls that table, honouring each step's `requires` edges, `optional` flag, and `gate` (`review`, `addon:*`, `feature:*`). There is no Temporal and no queue broker.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Postgres 16, Redis.
- Frontend: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4.
- Hosting: Render (one free web service, worker in-process), Supabase Postgres, Upstash Redis, Cloudflare R2, Vercel for the frontend.
- Tests: pytest (903 passing at the last full run) and vitest (66 passing).

## Branching and PRs

Create a fresh feature branch per task off `main`, named for the work (`fix/`, `feat/`, `docs/`, `chore/`). Push it, open a PR, and do not merge to `main` without an explicit green light. Never push to `main` directly and never amend published commits. `gh pr create` works on this machine; the compare URL printed by `git push` is the fallback.

## Working rules

- Every `Bash` tool call must pass an explicit `timeout`. The 2-minute default kills `pytest`, `docker build`, and `npm ci` silently.
- Commit and push before ending a session. The stop hook blocks on uncommitted changes or unpushed commits.
- `.env.example` is generated from `Settings.model_fields` by `scripts/gen_env_example.py`. Never hand-edit it. Regenerate after adding or removing a setting, then run `just env-check`; the drift check is a hard gate in CI.

## Commands

```bash
just check       # ruff check src tests alembic + pytest -m "not db and not ffmpeg" -q
just test        # pytest -q (needs Postgres on 5433 and ffmpeg for full green)
just dev         # uvicorn listingjet.main:app --reload --port 8000
just worker      # python -m listingjet.pipeline.worker (standalone; rarely needed)
just env-check   # scripts/gen_env_example.py --check

# Windows (no POSIX `just` runtime) — call the venv binaries directly:
.venv/Scripts/ruff.exe check src tests alembic scripts
.venv/Scripts/pytest.exe -m "not db and not ffmpeg" -q
.venv/Scripts/python.exe -m uvicorn listingjet.main:app --reload --port 8000
.venv/Scripts/python.exe -m listingjet.pipeline.worker
.venv/Scripts/python.exe scripts/gen_env_example.py --check
```

## CI

`.github/workflows/test.yml` runs on every PR and on push to `main`: a `backend` job (Postgres on 5433, Redis, Alembic, ffmpeg, `ruff check src tests alembic scripts`, the `.env.example` drift check, `pytest`) and a `frontend` job (`npm ci`, lint, `tsc --noEmit`, `vitest run`, `npm run build`). `.github/workflows/deploy.yml` hits the Render deploy hook (`RENDER_DEPLOY_HOOK_API`) on push to `main` only. `.github/workflows/docker.yml` builds the Docker image without pushing it, on every PR and on push to `main`.

## Where things live

The repo directory is `launchlens` and the local DB is named `launchlens`, but the Python package, Docker user, and all branding are `listingjet`. Do not recreate `src/launchlens/`.

| What | Where |
|---|---|
| FastAPI app factory, router mounts, lifespan | `src/listingjet/main.py` |
| Pipeline definition: the `Step(...)` list, `requires`, gates | `src/listingjet/pipeline/definition.py` |
| Job claiming, retries, gate evaluation; standalone worker entrypoint | `src/listingjet/pipeline/runner.py`, `pipeline/worker.py` |
| Step implementations, one class per step | `src/listingjet/agents/` |
| Providers: Claude text and vision, OpenAI images, Runway, Canva; `mock.py` when `USE_MOCK_PROVIDERS=true` | `src/listingjet/providers/` |
| HTTP routers and per-route schemas | `src/listingjet/api/`, `api/schemas/` |
| SQLAlchemy models | `src/listingjet/models/` |
| Business logic: auth, billing, credits, email, audit, rate limit | `src/listingjet/services/` |
| Feature flags | `src/listingjet/features.py` |
| `Settings`, AI price table, credit tiers | `src/listingjet/config/` (`__init__.py`, `ai_rates.py`, `tiers.py`) |
| Migrations, linear 001 to 056 | `alembic/versions/` |
| Backend test suite | `tests/` |
| Frontend App Router code; `lib/generated/api.d.ts` via `npm run generate-api` | `frontend/src/` |
| Seed, smoke, and env-generation scripts | `scripts/` |

## Constraints and gotchas

- Migration head is `056_video_asset_metadata`. Chain the next migration off it.
- `FEATURES=` is a comma-separated list of `learning`, `health_score`, `performance_intelligence`, `help_agent`, `microsite`, `webhooks`, `listing_permissions`. All off by default. Routers are selected at app start, so changing it requires restarting the API.
- Routers mount at their own prefix (`/auth`, `/listings`, `/admin`, and so on). There is no `/v1`. Health is at `/health` and `/health/deep`; `/ready` does not exist. Exception: the SSE stream is at `GET /sse/listings/{id}/events` (with `?token=`), because `api/listing_events.py` already owns `GET /listings/{id}/events`.
- The worker runs inside the API process (`WORKER_ENABLED`, default true). There is no separate worker service on Render.
- Render's free tier sleeps when idle, which pauses the worker and the hourly watchdog with it. Supabase free pauses a project after 7 idle days.
- ffmpeg must be on PATH or pointed at by `FFMPEG_BIN`; `video_baseline` and `social_cuts` shell out to it.
- With `USE_MOCK_PROVIDERS=true` every photo comes back `is_photo=True` at quality 85, so coverage and packaging never reject anything in a mock run.

## Docs

[README.md](README.md) · [free-tier setup runbook](docs/runbooks/free-tier-setup.md) · [design spec](docs/superpowers/specs/2026-09-05-free-tier-rework-design.md) · [MASTER_TODO.md](MASTER_TODO.md)
