# ListingJet — Claude Code Session Guide

## What this project is

**ListingJet** is a SaaS platform that automates real estate listing media: agents upload property photos and get back MLS export bundles, AI descriptions, branded flyers, social content, a video tour, and a 3D floorplan — all processed through a 14-agent Temporal workflow pipeline.

- **Backend:** FastAPI + Temporal + PostgreSQL + Redis, Python 3.12, Alembic migrations
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, TypeScript
- **Infra:** Render (API + worker), Supabase Postgres, Upstash Redis, Cloudflare R2 (media), Temporal Cloud — see `render.yaml`. (Migrated off AWS; the CDK in `infra/` is decommission-only — see `infra/README.md`.)
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
of 2 minutes will kill long-running commands (`cdk diff`, `pytest`,
`docker build`, `npm ci`) silently — always set a ceiling that matches the
expected runtime.

---

## Running the project

```bash
# Start all services (postgres, redis, temporal, api, worker, localstack)
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
| Temporal worker entry | `worker.py` |
| Temporal client wrapper | `temporal_client.py` |
| DB engine / session | `database.py` |
| Logging + telemetry setup | `logging_config.py`, `telemetry.py` |
| API routers | `api/` |
| Per-route Pydantic schemas | `api/schemas/` |
| Temporal workflows | `workflows/` |
| Temporal activities | `activities/` |
| Pipeline agents | `agents/` |
| SQLAlchemy models | `models/` |
| Business-logic services | `services/` (auth, billing, credits, email, audit, rate-limit, scrapers, etc.) |
| AI/media provider adapters | `providers/` (Claude, OpenAI, Gemma, Canva, ElevenLabs, Kling, Google Vision); generated Canva SDK under `providers/canva_generated/`; prompt templates under `providers/templates/` |
| FastAPI middleware | `middleware/` |
| Pricing-tier configuration | `config/` (currently `tiers.py`) |
| Observability (Prometheus + Sentry) | `monitoring/` |
| Email templates (Jinja) | `templates/email/` |
| Utility helpers | `utils/` |
| Shared schemas (stub) | `schemas/` — empty today; active schemas live under `api/schemas/` |

### Backend support

| What | Where |
|---|---|
| Alembic migrations | `alembic/versions/` (001→050, linear) |
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
| CDK stacks | `infra/stacks/` |
| Dockerfile + compose | `Dockerfile`, `docker-compose.yml`, `docker/` |
| Design tokens / system | `design-system/listingjet/` |
| Vercel config | `vercel.json` |
| Railway config (legacy) | `railway.json` |

### Docs & planning

| What | Where |
|---|---|
| Master task list | `MASTER_TODO.md` |
| General TODOs | `TODO.md`, `TODO-video-template.md` |
| Pre-launch infra checklist | `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` |
| Other specs, PRDs, handoffs | `docs/` |
| LLM-friendly project overview | `PROJECT_OVERVIEW_FOR_LLM.md` |
| Cloud migration notes | `CLOUD_MIGRATION_GUIDE.md` |

---

## What's been done (don't redo these)

All P2/P3 feature work is complete. The full list is in `MASTER_TODO.md`. Notable recent work:

- XGBoost phase 2 weight scoring in `weight_manager.py`
- CI: `test.yml` has frontend job + coverage; `deploy.yml` has Trivy CRITICAL scan + worker image push
- Release automation: `.releaserc.json` + `release.yml` (semantic-release on `main`)
- LocalStack in `docker-compose.yml` for local S3 mock
- MLS image resize profiles (`MLS_PROFILES` in `mls_export.py`)
- Email blast endpoint: `POST /listings/{id}/email-blast`
- Real-time admin usage SSE: `GET /admin/usage-stream` + `UsageDashboard` component
- 3D dollhouse viewer: `DollhouseViewer` Canvas component wired into `DollhouseCard`
- `LearningWorkflow` as standalone Temporal workflow (fire-and-forget from pipeline)
- Workflow cancellation (`TemporalClient.cancel_workflow()`)
- Per-user daily quota + configurable plan limits via admin API

---

## Migration off AWS → Render + Supabase + R2 (in progress)

The platform is moving off AWS to **Render** (API + worker), **Supabase**
(Postgres), **Upstash** (Redis), **Cloudflare R2** (media), and **Temporal
Cloud**. The **code + config is done**; what remains is operational (provision
the accounts, sync data, flip DNS, decommission AWS).

- **Compute / DB / cache / Temporal cutover** → `docs/runbooks/render-supabase-cutover.md`
- **Storage (S3 → R2) cutover** → `docs/runbooks/r2-cutover.md`
- **Deploy target** → `render.yaml` (Render blueprint); CI is `.github/workflows/deploy.yml` (test-gated Render deploy hooks).
- **AWS CDK** in `infra/` is **decommission-only** — used solely for the final `cdk destroy`. See `infra/README.md`.

The old AWS RDS encryption / SES / pre-launch-resize / cost-collection P0 items
are obsolete under the new stack and have been removed.

---

## Important constraints

- **Never push to `main` directly** — go through the feature branch
- **Never amend published commits** — create new commits
- **Migration chain is 001→050 linear** — next migration must be `051_...` with `down_revision = "050_tenant_admin_controls"`
- Routes are mounted at their router prefix directly (e.g. `/auth/...`, `/listings/...`, `/demo/...`) — there is no `/v1` prefix in the running app despite past plans. Health endpoints (`/health`, `/health/deep`) are at their literal paths; `/ready` is not implemented.
- The stop hook in `~/.claude/settings.json` will block you from stopping if there are uncommitted changes or unpushed commits — commit and push before ending the session.
