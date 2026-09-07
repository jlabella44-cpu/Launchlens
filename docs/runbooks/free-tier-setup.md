# Free-Tier Setup Runbook

How to stand up a complete ListingJet environment from nothing, using only free plans. Follow the sections in order; each one produces values you paste into the next.

## Overview

| Piece | Where it runs | Plan |
|---|---|---|
| API + pipeline worker | Render web service, Docker, `oregon` | Free |
| Postgres (RLS, `pipeline_jobs`) | Supabase | Free |
| Redis (rate limits, token revocation) | Upstash | Free |
| Media objects | Cloudflare R2 | Free tier, 10 GB, no egress charge |
| Frontend | Vercel | Hobby |
| Errors | Sentry | Developer, optional |

Hosting cost is $0. The only spend is AI usage: Anthropic and OpenAI are pay as you go, and Runway needs a prepaid credit balance. A single listing without the AI video add-on runs well under $1; with the add-on, budget a few dollars.

The worker is not a separate service. It runs inside the API process when `WORKER_ENABLED=true`, which `render.yaml` sets for you.

## Accounts

Work through these in order. Keep a scratch file of the values as you go.

### 1. Supabase (Postgres)

1. Create a project in a region close to Render's `oregon`, that is US West. Save the database password.
2. Create a dedicated login role rather than using `postgres`. The app relies on Row-Level Security for tenant isolation and a superuser bypasses it:
   ```sql
   CREATE ROLE listingjet LOGIN PASSWORD '<password>' NOBYPASSRLS;
   GRANT ALL ON SCHEMA public TO listingjet;
   ```
   Confirm with `SELECT rolbypassrls FROM pg_roles WHERE rolname = 'listingjet';` — it must be `false`.
3. Project Settings, Database, Connection string:
   - Transaction pooler (port 6543) becomes `DATABASE_URL`. Also set `DB_USE_PGBOUNCER=true`, otherwise asyncpg's prepared-statement cache fails under load with `prepared statement "__asyncpg_..." already exists`.
   - Direct connection (port 5432) becomes `DATABASE_URL_SYNC`. Alembic uses this one.

### 2. Upstash (Redis)

1. Create a Redis database in US West. Set eviction to `noeviction`; the keys are rate-limit counters and revocation markers, not a droppable cache.
2. Copy the `rediss://` URL into `REDIS_URL`. Two `s` characters — a plain `redis://` URL fails the TLS handshake.

### 3. Cloudflare R2 (media)

1. R2, Create bucket, name `listingjet-media`, location hint auto.
2. Enable the public bucket domain (Settings, Public access). That hostname becomes `NEXT_PUBLIC_MEDIA_HOST` on Vercel.
3. Manage R2 API Tokens, Create API token: Object Read and Write, scoped to `listingjet-media`. Copy the Access Key ID, Secret Access Key, and the endpoint URL, which looks like `https://<account-id>.r2.cloudflarestorage.com`. They are shown once.
   - `S3_BUCKET_NAME=listingjet-media`
   - `S3_ENDPOINT_URL=<endpoint>`
   - `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
   - `AWS_REGION=auto`
4. Bucket Settings, CORS Policy: allow your Vercel origin and preview URLs with `GET`, `PUT`, `POST`. The upload wizard posts directly to R2 with a presigned POST.

### 4. Anthropic and OpenAI

Create keys at https://console.anthropic.com/settings/keys and https://platform.openai.com/api-keys. They become `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`. Both providers are pay as you go, so add a small spend cap while you are testing.

### 5. Runway (video)

Sign up at the Runway developer portal, create an organization, and add $10 of credits. Copy the key into `RUNWAY_API_KEY`. Model routing is already set by `RUNWAY_INTERIOR_MODEL=gen4_turbo` and `RUNWAY_EXTERIOR_MODEL=veo3.1_fast`.

### 6. Resend (email)

Create a sending key at https://resend.com/api-keys, verify your sending domain, and set `RESEND_API_KEY` plus `EMAIL_ENABLED=true`.

### 7. Render (API and worker)

1. New, Blueprint, point it at this repo. Render reads [`render.yaml`](../../render.yaml) and proposes one service, `listingjet-api`, on the free plan.
2. It creates the `listingjet-shared` environment group. Fill in every `sync: false` key from the table below.
3. `autoDeploy` is off by design. Service, Settings, Deploy Hook: copy the URL and add it to the GitHub repository secrets as `RENDER_DEPLOY_HOOK_API` — that is the exact name `.github/workflows/deploy.yml` reads.
4. `WORKER_ENABLED=true` and `WORKER_CONCURRENCY=2` are already in the blueprint. Do not create a second service for the worker.
5. Render injects `PORT`; `entrypoint.sh` honours it. Do not hardcode 8000.

### 8. Vercel (frontend)

1. Import the repo and set the root directory to `frontend/`. Hobby plan.
2. `frontend/vercel.json` already sets `NEXT_PUBLIC_API_URL=/api` and rewrites `/api/:path*` to `https://api.listingjet.ai/:path*`. Point that rewrite at your Render service URL if you are not using the `api.listingjet.ai` domain.
3. Set `NEXT_PUBLIC_MEDIA_HOST` to the R2 public bucket hostname. `next.config.ts` fails a production build without it.

### 9. Optional extras

- **Sentry** — create a project, copy the DSN into `SENTRY_DSN`. Leave it unset to disable.
- **Stripe** — test-mode keys are enough for a non-billing environment: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, plus the `STRIPE_PRICE_*` ids if you want checkout to work.
- **Canva** — `CANVA_API_KEY` and `CANVA_DEFAULT_TEMPLATE_ID` for branded flyers. Without them the `brand` step fails, and because it is optional the pipeline continues.
- **Google** — `GOOGLE_API_KEY` and `GOOGLE_OAUTH_CLIENT_ID` are only needed for Google Drive listing import.

## Environment values

Every key in the `listingjet-shared` group in `render.yaml`, and where its value comes from. Keys marked "blueprint" already have a literal value in `render.yaml` and need no action.

| Key | Source |
|---|---|
| `DATABASE_URL` | Supabase transaction pooler URL, port 6543 |
| `DATABASE_URL_SYNC` | Supabase direct URL, port 5432 |
| `DB_USE_PGBOUNCER` | Blueprint, `true` |
| `TRUSTED_PROXY_COUNT` | Blueprint, `1` (Render is one proxy hop) |
| `REDIS_URL` | Upstash `rediss://` URL |
| `S3_BUCKET_NAME` | R2 bucket name, `listingjet-media` |
| `S3_ENDPOINT_URL` | R2 API token screen |
| `S3_ACCESS_KEY_ID` | R2 API token screen |
| `S3_SECRET_ACCESS_KEY` | R2 API token screen |
| `AWS_REGION` | Blueprint, `auto` (required by R2) |
| `JWT_SECRET` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FIELD_ENCRYPTION_KEY` | Generate a Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `FRONTEND_URL` | Blueprint, your Vercel domain |
| `CORS_ORIGINS` | Blueprint, comma-separated origins allowed to call the API |
| `FEATURES` | Blueprint, empty. See `src/listingjet/features.py` for the seven flag names |
| `STRIPE_SECRET_KEY` | Stripe dashboard, restricted key |
| `STRIPE_WEBHOOK_SECRET` | Stripe dashboard, webhook endpoint |
| `OPENAI_API_KEY` | OpenAI platform |
| `ANTHROPIC_API_KEY` | Anthropic console |
| `GOOGLE_API_KEY` | Google Cloud console, Drive import only |
| `CANVA_API_KEY` | Canva developer portal, optional |
| `CANVA_DEFAULT_TEMPLATE_ID` | Canva template id, optional |
| `RUNWAY_API_KEY` | Runway developer portal |
| `EMAIL_ENABLED` | Blueprint, `true` |
| `RESEND_API_KEY` | Resend dashboard |
| `SENTRY_DSN` | Sentry project settings, optional |

Anything else the app reads has a default in `Settings`; see [`.env.example`](../../.env.example) for the full list. Notable ones you may want to add to the group: `FFMPEG_BIN` if the image ever stops shipping ffmpeg on PATH, `RUNWAY_INTERIOR_MODEL` and `RUNWAY_EXTERIOR_MODEL` to change video routing, and `USE_MOCK_PROVIDERS=true` if you want a staging environment that spends nothing.

## First deploy

1. Push to `main`. `.github/workflows/test.yml` runs the backend and frontend jobs, and `.github/workflows/deploy.yml` calls the Render deploy hook.
2. Render builds the Docker image, then runs `preDeployCommand` (`./entrypoint.sh migrate`), which applies Alembic migrations to Supabase. A non-zero exit aborts the deploy before traffic shifts.
3. Wait for the service to report live, then check both health endpoints:
   ```bash
   curl -fsS https://<service>.onrender.com/health
   curl -fsS https://<service>.onrender.com/health/deep
   ```
   `/health/deep` also confirms Redis and that the worker loop is ticking.
4. Create the first tenant, user, and listing. The frontend wizard is the normal path. `scripts/seed_sample_listing.py` does the same thing headlessly (tenant, admin user, one listing with 12 generated photos, pipeline enqueued) and can be pointed at the deployed database, but it is written for `USE_MOCK_PROVIDERS=true` runs, so only use it against a throwaway environment:
   ```bash
   DATABASE_URL=<supabase pooler> DATABASE_URL_SYNC=<supabase direct> \
     python scripts/seed_sample_listing.py
   ```

## Smoke test

1. Sign in on the Vercel frontend and create a listing.
2. Upload photos through the creation wizard. This exercises the R2 presigned POST and Supabase writes.
3. Watch progress on `GET /sse/listings/{id}/events?token=<jwt>`. Steps should move through `ingestion`, `photo_analysis`, `coverage`, `floorplan`, `packaging`, then stop at `await_review`.
4. Approve the listing. The post-review steps (`content_social`, `mls_export`, `distribution`) run.
5. Download the MLS bundle and the marketing bundle from the listing page.
6. Play the tour video. `video_baseline` is the free ffmpeg tour; `video_ai` only runs when the `ai_video_tour` add-on is active on that listing.

## Free-tier gotchas

- **Render sleeps.** A free web service spins down after about 15 minutes with no traffic. The first request afterwards takes roughly 30 seconds. Because the worker and the hourly watchdog live in the same process, they are asleep too: nothing progresses while the service is down. On a day you are actively testing, point an external cron at `/health` every 10 minutes to keep it warm.
- **Supabase pauses.** A free project pauses after 7 idle days and must be restored from the dashboard. Restoring is a few minutes and loses nothing.
- **Upstash counts commands.** The free plan has a daily command quota. Token revocation does one `EXISTS` per authenticated request, which is the dominant consumer; heavy polling from a frontend bug can burn through the quota fast.
- **R2 egress is free**, so serving media from the public bucket domain costs nothing. Storage above 10 GB is what eventually bills.
- **Runway URLs expire** in roughly 24 to 48 hours. `video_ai` downloads each clip as soon as the task finishes, so nothing depends on the Runway URL afterwards. Do not store one.
- **Vercel Hobby is non-commercial.** Moving to paid traffic means moving to Pro.
- **Free tiers have no backups worth the name.** Take a Supabase dump before anything destructive.

## Rotating secrets

Every key above has a rotation procedure, downtime risk, and cutover order in [`secret-rotation.md`](secret-rotation.md).
