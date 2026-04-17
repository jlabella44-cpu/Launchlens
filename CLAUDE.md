# ListingJet — Claude Code Session Guide

## What this project is

**ListingJet** is a SaaS platform that automates real estate listing media: agents upload property photos and get back MLS export bundles, AI descriptions, branded flyers, social content, a video tour, and a 3D floorplan — all processed through a 14-agent Temporal workflow pipeline.

- **Backend:** FastAPI + Temporal + PostgreSQL + Redis, Python 3.12, Alembic migrations
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, TypeScript
- **Infra:** AWS ECS Fargate + ECR + RDS + ElastiCache + S3, CDK in `infra/`
- **Tests:** pytest + pytest-cov, vitest for frontend

---

## Active branch

All work goes on: **`claude/run-prod-migrations-IerKk`**

```bash
git checkout claude/run-prod-migrations-IerKk
git pull origin claude/run-prod-migrations-IerKk
```

Push when done:
```bash
git push -u origin claude/run-prod-migrations-IerKk
```

Do **not** push to `main` or create a PR unless explicitly asked.

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

| What | Where |
|---|---|
| API routers | `src/listingjet/api/` |
| Temporal workflows | `src/listingjet/workflows/` |
| Pipeline agents | `src/listingjet/agents/` |
| Alembic migrations | `alembic/versions/` (001→050, linear) |
| CDK infra | `infra/stacks/` |
| Frontend pages | `frontend/src/app/` |
| Frontend components | `frontend/src/components/` |
| Master task list | `MASTER_TODO.md` |
| Pre-launch infra checklist | `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` |

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
- Tenant soft-delete (`deactivated_at`), `bypass_limits`, `plan_overrides` (migration 050)
- `LearningWorkflow` as standalone Temporal workflow (fire-and-forget from pipeline)
- Workflow cancellation (`TemporalClient.cancel_workflow()`)
- Per-user daily quota + configurable plan limits via admin API

---

## Remaining P0 items (production blockers)

These all require **external AWS actions** — no code changes needed, just ops work:

### 1. SES production access
- Still waiting on AWS approval
- Once approved: create SMTP IAM user → generate credentials → store in `listingjet/app` Secrets Manager as `SMTP_PASSWORD`
- Also set `smtp_host`, `smtp_port`, `smtp_user`, `email_from`
- Then force ECS redeploy: `aws ecs update-service --cluster listingjet --service listingjet-api --force-new-deployment`

### 2. Run `cdk deploy`
```bash
cd infra
pip install -r requirements.txt
cdk deploy --all
```
IAM policies are currently inline (applied manually). `cdk deploy` makes them permanent and managed.

### 3. RDS encrypted-storage migration (~30-60 min downtime)
The live RDS instance `kjyxgeldpfef` is unencrypted. Full runbook in `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` section A:
1. Snapshot → copy with encryption → restore → update `DATABASE_URL` secret → restart ECS → delete old instance
2. Then uncomment `storage_encrypted=True` in `infra/stacks/database.py` and re-run `cdk deploy`

### 4. Pre-launch infra revert
See `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` — infra was deliberately undersized while there are zero users. Before real users land, apply in `infra/stacks/database.py`:
- RDS: `t4g.micro` → `t4g.small`, backup retention 1 day → 7 days, consider Multi-AZ
- Redis: `cache.t4g.micro` → `cache.t4g.small`, single-node → 2-node with failover
- ECS: increase CPU/memory on API and worker task definitions
- Then `cdk deploy`

### 5. Cost data to collect (after 7–14 days of traffic)
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
- **Migration chain is 001→050 linear** — next migration must be `051_...` with `down_revision = "050_tenant_admin_controls"`
- All feature routes are under `/v1` prefix. Health endpoints (`/health`, `/ready`, `/health/deep`) are unversioned.
- The stop hook in `~/.claude/settings.json` will block you from stopping if there are uncommitted changes or unpushed commits — commit and push before ending the session.
