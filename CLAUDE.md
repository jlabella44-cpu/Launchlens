# ListingJet — Claude Code Session Guide

## What this project is

**ListingJet** is a SaaS platform that automates real estate listing media: agents upload property photos and get back MLS export bundles, AI descriptions, branded flyers, social content, a video tour, and a 3D floorplan — all processed through a 14-agent Temporal workflow pipeline.

- **Backend:** FastAPI + Temporal + PostgreSQL + Redis, Python 3.12, Alembic migrations
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, TypeScript
- **Infra:** AWS ECS Fargate + ECR + RDS + ElastiCache + S3, CDK in `infra/`
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

- API versioning (`/v1` prefix on all routes); test suite uses transport-level path rewriting so no test changes needed
- XGBoost phase 2 weight scoring in `weight_manager.py`
- CI: `test.yml` has frontend job + coverage; `deploy.yml` has Trivy CRITICAL scan + worker image push
- `staging.yml` workflow: push to `staging` branch → test → build → migrate → deploy → smoke test (`/health` + `/ready`)
- Release automation: `.releaserc.json` + `release.yml` (semantic-release on `main`)
- LocalStack in `docker-compose.yml` for local S3 mock
- MLS image resize profiles (`MLS_PROFILES` in `mls_export.py`)
- Email blast endpoint: `POST /v1/listings/{id}/email-blast`
- Real-time admin usage SSE: `GET /v1/admin/usage-stream` + `UsageDashboard` component
- 3D dollhouse viewer: `DollhouseViewer` Canvas component wired into `DollhouseCard`
- `LearningWorkflow` as standalone Temporal workflow (fire-and-forget from pipeline)
- Workflow cancellation (`TemporalClient.cancel_workflow()`)
- Per-user daily quota + configurable plan limits via admin API

---

## Planned work — not yet shipped

- **Tenant admin controls** — soft-delete (`deactivated_at`), `bypass_limits`, and `plan_overrides` columns on `tenants`. Previously listed here as shipped under "migration 050", but neither the migration nor the model changes ever landed (verified 2026-04-20: no occurrence of those identifiers anywhere in the repo; last migration on disk is `049_team_invite_tokens`). Scope for a future PR: migration adding the three columns, `Tenant` model fields, auth/resolution filter on `deactivated_at`, quota/rate-limit bypass on `bypass_limits`, tier-config merge for `plan_overrides`, admin API endpoints. Touches auth + billing — requires manual review per the branching rules below.

---

## Remaining P0 items (production blockers)

These all require **external AWS actions** — no code changes needed, just ops work:

### 1. Wire up a working email provider
Current prod reality (verified 2026-04-16): `email_enabled` is unset in the
api/worker ECS task defs, so `get_email_service()` returns `NoOpEmailService`
and **no transactional email is actually being sent**. The
`listingjet/app` secret has `RESEND_API_KEY` set and `SMTP_PASSWORD` empty,
but the code has no Resend integration — only `EmailService` (SMTP),
`SESEmailService`, and `NoOpEmailService` in `src/listingjet/services/email.py`.

Pick one and finish the wiring:
- **Resend via SMTP relay** (simplest): set `SMTP_HOST=smtp.resend.com`,
  `SMTP_USER=resend`, plumb `RESEND_API_KEY` → `SMTP_PASSWORD` secret,
  set `EMAIL_ENABLED=true` in task def, redeploy.
- **Resend native**: add `resend` Python package, write `ResendEmailService`
  subclass, gate on a new `resend_enabled` setting.
- **SES**: wait for prod access approval, set `SES_ENABLED=true`,
  `EMAIL_ENABLED=true`, redeploy.

### 2. RDS encrypted-storage migration (~30-60 min downtime)
The live RDS instance `kjyxgeldpfef` is unencrypted. Full runbook in `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` section A:
1. Snapshot → copy with encryption → restore → update `DATABASE_URL` secret → restart ECS → delete old instance
2. Then uncomment `storage_encrypted=True` in `infra/stacks/database.py` and re-run `cdk deploy`

### 3. Pre-launch infra revert
See `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` — infra was deliberately undersized while there are zero users. Before real users land, apply in `infra/stacks/database.py`:
- RDS: `t4g.micro` → `t4g.small`, backup retention 1 day → 7 days, consider Multi-AZ
- Redis: `cache.t4g.micro` → `cache.t4g.small`, single-node → 2-node with failover
- ECS: increase CPU/memory on API and worker task definitions
- Then `cdk deploy`

### 4. Cost data to collect (after 7–14 days of traffic)
See `MASTER_TODO.md` "Cost Optimization" section — list of AWS Cost Explorer / Compute Optimizer / CloudWatch queries to run and bring back for right-sizing decisions.

---

## Staging environment setup (new — needs wiring)

`staging.yml` workflow is ready but needs these GitHub secrets/vars configured under the **`staging` environment** in repo settings:

| Name | Type | Value |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN_STAGING` | Secret | ARN of IAM role for staging deploys |
| `STAGING_URL` | Variable | e.g. `https://api-staging.listingjet.com` |

Staging ECS resources expected:
- Cluster: `listingjet-staging`
- Services: `listingjet-api-staging`, `listingjet-worker-staging`

---

## Important constraints

- **Never push to `main` directly** — go through the feature branch
- **Never amend published commits** — create new commits
- **Migration chain is 001→049 linear** — next migration must be `050_...` with `down_revision = "049_team_invite_tokens"`
- All feature routes are under `/v1` prefix. Health endpoints (`/health`, `/ready`, `/health/deep`) are unversioned.
- The stop hook in `~/.claude/settings.json` will block you from stopping if there are uncommitted changes or unpushed commits — commit and push before ending the session.
