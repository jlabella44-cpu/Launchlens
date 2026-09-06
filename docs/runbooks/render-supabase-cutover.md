# Render + Supabase Cutover Runbook (off AWS)

Moves ListingJet's **compute** (ECS Fargate → Render), **database** (RDS → Supabase),
and **cache** (ElastiCache → Upstash). The pipeline runs in-process on the worker,
polling a job table in Postgres (`src/listingjet/pipeline/`) — there is no separate
workflow-engine service to provision or cut over. Storage (S3 → Cloudflare R2) is
covered separately in [`r2-cutover.md`](./r2-cutover.md) — do that one first or in parallel.

All the **code** for this is already in place:
- `render.yaml` — Render blueprint for the API (web) + worker services.
- `src/listingjet/pipeline/worker.py` — polls the job table; runs standalone via `python -m listingjet.pipeline.worker` or in-process alongside the API.
- `db_use_pgbouncer` in config — disables asyncpg's prepared-statement cache for the Supabase pooler.
- `.github/workflows/deploy.yml` — test-gated Render deploy via deploy hooks (replaces the ECS/ECR pipeline).

This runbook is the **operational** side: provisioning the managed services, moving data, flipping DNS, and decommissioning AWS.

> **Order of operations.** Storage (R2) and DB (Supabase) data syncs can run ahead
> of time with the app still live on AWS. The actual cutover is a DNS/secret flip
> with a short read-only window for the DB copy. Plan for ~15–30 min of write
> downtime during the final DB sync, or use logical replication for near-zero.

---

## 0. Prerequisites

- Accounts: [Render](https://render.com), [Supabase](https://supabase.com), [Upstash](https://upstash.com), [Cloudflare](https://cloudflare.com) (for R2 + DNS).
- Local: `psql`, `pg_dump`/`pg_restore` (Postgres 16 client), AWS CLI logged in to the ListingJet account, `rclone` (for R2).
- The R2 cutover (`r2-cutover.md`) done or in flight.

---

## 1. Provision the managed services

### 1a. Supabase (Postgres)
1. Create a project (region close to Render's `oregon` → US West). Save the DB password.
2. **Project Settings → Database → Connection string**:
   - **Direct** (port 5432) → `DATABASE_URL_SYNC` (Alembic, `pg_restore`).
   - **Transaction pooler** (port 6543) → `DATABASE_URL`. Set `DB_USE_PGBOUNCER=true`.
3. ListingJet uses **Row-Level Security** (`app.current_tenant`). RLS policies travel with the schema dump, so nothing special here — but do **not** run the app as the Supabase `postgres` superuser if you can avoid it (superusers bypass RLS). Create a dedicated `listingjet` login role with `BYPASSRLS = false` and use it in both URLs. See `docs/PROJECT_OVERVIEW_FOR_LLM.md` for the RLS pattern.

### 1b. Upstash (Redis)
1. Create a Redis database (region = US West). Eviction: `noeviction` (we use it for rate-limiting + sessions, not as a cache that can drop keys silently).
2. Copy the **`rediss://`** URL (TLS) → `REDIS_URL`. `redis.asyncio.from_url` handles `rediss://` natively; no code change.

### 1c. Render (compute)
1. **New → Blueprint**, point at this repo. Render reads `render.yaml` and proposes `listingjet-api` (web) + `listingjet-worker`.
2. It also creates the `listingjet-shared` env group. Fill in every `sync: false` key (DB, Redis, R2, Stripe, providers, Resend, Sentry — see `.env.production.example`).
3. Create the services but **don't** point DNS at them yet.
4. **Deploy hooks**: each service → Settings → Deploy Hook. Add to GitHub repo secrets as `RENDER_DEPLOY_HOOK_API` and `RENDER_DEPLOY_HOOK_WORKER` (used by `deploy.yml`). `autoDeploy` is off, so deploys only fire after CI is green.

---

## 2. Migrate the database (RDS → Supabase)

Find the live RDS endpoint:
```bash
aws rds describe-db-instances \
  --query "DBInstances[?DBInstanceIdentifier=='listingjet-postgres-encrypted'].Endpoint.Address" \
  --output text
```

**Option A — dump/restore (simplest, ~15–30 min write downtime).**
1. Put the app in maintenance / scale ECS services to 0 to stop writes:
   ```bash
   aws ecs update-service --cluster listingjet --service listingjet-api --desired-count 0
   aws ecs update-service --cluster listingjet --service listingjet-worker --desired-count 0
   ```
2. Dump and restore (schema + data, RLS policies and roles included):
   ```bash
   pg_dump --no-owner --no-privileges -Fc \
     "postgresql://listingjet:<pass>@<rds-endpoint>:5432/listingjet" > listingjet.dump
   pg_restore --no-owner --no-privileges -d "$DATABASE_URL_SYNC" listingjet.dump
   ```
3. Stamp Alembic and verify head matches the repo:
   ```bash
   DATABASE_URL_SYNC="<supabase-direct>" alembic current   # should report 051_…
   ```
   The migration chain is 001→051 linear; the dump already carries the schema, so do **not** run `upgrade head` against a freshly-restored DB unless `current` is behind.

**Option B — logical replication (near-zero downtime).** Use Supabase's external-source
replication or `pglogical` from RDS. Heavier setup; only worth it if the write-downtime
window in Option A is unacceptable. For a pre-/low-traffic launch, Option A is fine.

Sanity check row counts on a few core tables (`tenants`, `users`, `listings`, `credit_accounts`) match between source and target before proceeding.

---

## 3. Cut over

1. Confirm the `listingjet-shared` env group on Render has the **Supabase**, **Upstash**, and **R2** values filled in.
2. Trigger the first Render deploy (push to `main`, or hit the deploy hooks). The API's `preDeployCommand` runs `alembic upgrade head` — a no-op if the restore was current, a safety net otherwise.
3. Watch both services reach **live**; the API health check (`/health`) must be green (it pings Postgres); `/health/deep` also confirms Redis and that the pipeline worker is ticking.
4. **Repoint the frontend.** `vercel.json` rewrites `/api/*` → `https://api.listingjet.ai`. Update the `api.listingjet.ai` DNS record (Cloudflare) to the Render service's URL/custom domain. Add `api.listingjet.ai` as a custom domain on the `listingjet-api` Render service so its TLS cert provisions.
5. Re-run any listings that were mid-pipeline at the RDS freeze (their jobs didn't survive the database cutover). Find them by `listings.status` in (`PROCESSING`, `REVIEW`, `EXPORTING`) and retry from the admin UI.

---

## 4. Smoke test

- Sign in, create a listing, upload photos (exercises R2 presigned POST + Supabase writes).
- Watch the pipeline run end-to-end (exercises the worker + R2 reads/writes).
- Approve + export a listing (MLS bundle presigned URL from R2).
- Confirm a transactional email arrives (Resend).
- Tail Render logs for both services — no `StorageError`, no DB connection errors.

---

## 5. Decommission AWS (Phase 3 — do after a confidence window)

**Wait a week or two** with the new stack healthy before tearing anything down — AWS is your rollback.

Once confident, tear down the CDK-managed infra. The stacks are in `infra/`:
```bash
cd infra && pip install -r requirements.txt
cdk destroy ListingJetMonitoring ListingJetCI ListingJetServices ListingJetCDN ListingJetDatabase ListingJetNetwork
```
Notes:
- `ListingJetDatabase` adopts the live RDS via the zombie-import path (see the docstring in `infra/stacks/database.py`). Confirm a final manual snapshot exists before destroy, or take one:
  `aws rds create-db-snapshot --db-instance-identifier listingjet-postgres-encrypted --db-snapshot-identifier final-pre-teardown`.
- The R2 cutover runbook covers deleting the S3 media bucket. Don't delete it until R2 has fully taken over.
- Delete the `listingjet/app` Secrets Manager secret and the GitHub OIDC deploy role last.
- Remove leftover GitHub repo secrets: `AWS_DEPLOY_ROLE_ARN`.

After teardown, delete the now-unused `infra/` directory and `cdk.json` in a follow-up PR (kept in-repo until now precisely so `cdk destroy` works).

---

## Rollback

Before DNS is flipped (step 3.4), rollback is trivial: scale the ECS services back up
(`--desired-count 1`) and you're back on AWS — the RDS data is untouched (we dumped, not
moved). After DNS is flipped and real writes have landed in Supabase, rolling back means
re-syncing Supabase→RDS for the delta, so treat the DNS flip as the point of no easy return
and smoke-test hard before it.

---

## Gotchas

- **Supabase pooler + asyncpg**: must set `DB_USE_PGBOUNCER=true`, else you'll see
  `prepared statement "__asyncpg_..." already exists` under load. Alembic uses
  `DATABASE_URL_SYNC` against the **direct** port (5432), not the pooler.
- **RLS / superuser**: don't run the app as Supabase `postgres` (superuser bypasses RLS,
  which would silently disable tenant isolation). Use a non-superuser `listingjet` role.
- **Upstash TLS**: the URL is `rediss://` (two s's). A plain `redis://` will fail the TLS handshake.
- **Render PORT**: Render injects `PORT`; `entrypoint.sh` already honors it. Don't hardcode 8000.
