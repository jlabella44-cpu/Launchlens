# ListingJet: back on track on free tiers, agents reworked

## Context

AWS is fully shut down and there is no production data to carry over. The 2026-09-01 efficiency review (`docs/reviews/2026-09-01-efficiency-and-cost-review.md`, branch `claude/project-efficiency-cost-review-wtjb1f`) found the codebase heavier than the product: three AI steps burn most of the money, Temporal is the largest fixed cost and barely used, four AI vendors do analysis work one could do, and a handful of security and stuck-state bugs must be fixed before anything else.

Decisions already made with the user:

- Clean restart. Fresh DB, seed with test listings.
- Hosting on free tiers. Small paid budget (tens of dollars) for AI calls; video only on demand.
- Temporal is replaced by a Postgres job table.
- All four output groups are core: photo curation + MLS bundle, copy + social, video tour + social cuts, floorplan + staging + flyer.
- Delete CMA reports, market tracker, IDX/RESO poller. Everything else speculative is feature-flagged off, not deleted.
- Video: ffmpeg Ken Burns baseline on every listing, Runway API (Kling 3.0 interiors, Veo 3.1 Fast exteriors) as the paid add-on. Runway chosen over Higgsfield because it is pay-as-you-go ($0.01/credit, $10 minimum) with every relevant model behind one key; Higgsfield's API bills against the consumer subscription and exposes fewer confirmed models.
- Claude for all text and vision (Haiku 4.5 per-photo, Sonnet 5 for copy/floorplan). OpenAI kept only for image generation (staging, dollhouse).
- Primary customer: solo agents and small teams.
- Approach: incremental rewrite in place. Keep FastAPI, models, Alembic, auth, billing, admin, review flow, Next.js app, and the 883-test suite.

Work happens on feature branches off `main`, one PR per phase, no merge without explicit approval (per `CLAUDE.md`). Every Bash call needs an explicit timeout.

## Target architecture

```
Vercel Hobby (Next.js)  --/api rewrite-->  Render free web service (Docker)
                                             |-- FastAPI app
                                             |-- worker loop (asyncio task in same process)
                                             |
                    Supabase Postgres <------+------> Upstash Redis
                    Cloudflare R2 (public bucket domain for images)
                    Anthropic (Haiku 4.5 / Sonnet 5), OpenAI images, Runway video, Resend, Sentry
```

Local dev: `docker-compose` with Postgres only (drop temporal, temporal-ui, clamav, jaeger, pgbouncer, postgres-test stays for tests). API + worker run from `uvicorn` locally.

Free-tier constraints to design around (verify limits at signup):
- Render free: web services only, 512 MB, spins down after 15 idle min. Worker runs inside the API process. A free external cron ping (`/health`) keeps it warm on test days.
- Supabase free pauses after 7 idle days; 500 MB.
- Vercel Hobby is non-commercial; fine for testing.

## Phase 1: security and correctness fixes (branch `fix/security-week1`)

Small, independent, ship first.

- `src/listingjet/api/deps.py:38` and `src/listingjet/middleware/tenant.py:35`: reject JWTs whose `type != "access"`.
- `src/listingjet/services/auth.py:104-108`: revocation check fails closed; use one shared `redis.asyncio` client on `app.state` (also replaces the 8 ad hoc sync clients found by `grep -rn "redis.from_url\|Redis(" src/`).
- Presigned upload endpoint in `src/listingjet/api/listings_media.py`: content-length ceiling (25 MB) and MIME allowlist (jpeg/png/heic/webp). Remove ClamAV references (`services/scanner.py`, `clamd` dep, compose service).
- `src/listingjet/main.py:161`: CORS origins from `settings.cors_origins` only, no wildcard vercel pattern.
- `src/listingjet/api/canva_oauth.py:122`: verify Canva JWT signature or drop the decode.
- `TRUSTED_PROXY_COUNT` becomes a setting, default 1 for Render.
- `src/listingjet/api/auth.py:151,167,176`: lockout errors log at error level and count as a failed attempt rather than being swallowed.
- `services/field_encryption.py`: raise in `app_env == "production"` when no key.
- Migration `052_tenant_indexes`: indexes on `users.tenant_id`, `events.tenant_id`, `outbox.tenant_id`, `audit_logs.tenant_id`. (Head is currently `051`, not `050` as CLAUDE.md claims. Confirm with `alembic heads`.)
- `frontend/next.config.ts`: `remotePatterns` for the R2 public domain (from `NEXT_PUBLIC_MEDIA_HOST`), drop the S3 patterns.

Tests: extend `tests/test_api/` auth tests for refresh-token-as-bearer (expect 401), upload limits (expect 413/415).

## Phase 2: job queue replaces Temporal (branch `feat/job-queue`)

### Schema
Migration `053_pipeline_jobs`:

```
pipeline_jobs
  id uuid pk, tenant_id, listing_id (fk listings, indexed),
  step text, status text (queued|running|done|failed|waiting),
  attempts int, max_attempts int, run_after timestamptz,
  locked_by text null, locked_at timestamptz null,
  payload jsonb, result jsonb, error text null,
  created_at, updated_at
  unique (listing_id, step)
```

### Pipeline definition
New `src/listingjet/pipeline/definition.py`: a list of `Step(name, agent_factory, requires=[...], timeout_s, max_attempts, optional=bool, gated_by_addon=None)`. Replaces `workflows/listing_pipeline.py`. Order:

```
ingestion
photo_analysis          requires ingestion
property_verification   requires ingestion (optional)
coverage                requires photo_analysis
virtual_staging         requires photo_analysis (addon, optional)
floorplan               requires photo_analysis
dollhouse_render        requires floorplan (optional)
packaging               requires coverage, floorplan
video_baseline          requires packaging (optional)
await_review            requires packaging   <- human gate; skipped when packaging auto-approves
content_social          requires await_review
brand                   requires content_social (optional)
video_ai                requires packaging, await_review (addon ai_video_tour, optional)
social_cuts             requires video_baseline|video_ai (optional)
mls_export              requires content_social, brand
distribution            requires mls_export
learning, health_score, performance_intelligence, microsite, social_event
                        requires distribution (each behind a feature flag, optional)
```

### Runner
New `src/listingjet/pipeline/runner.py`:
- `enqueue_pipeline(session, listing, addons)` inserts all steps as `queued` (gated steps skipped, `await_review` inserted as `waiting`).
- `claim_next(session, worker_id)`: `SELECT ... FOR UPDATE SKIP LOCKED WHERE status='queued' AND run_after <= now() AND all requires are done`. Pattern already exists in `services/outbox_poller.py`; reuse its loop shape.
- `run_job`: `asyncio.wait_for(agent.instrumented_execute(ctx), timeout_s)`. On success mark `done`, on exception increment attempts, set `run_after = now + backoff`, and when attempts exhausted mark `failed`; non-optional failure sets `Listing.state = FAILED` with `error` on the job. Non-retryable errors (`ValueError`, 4xx from providers) fail immediately.
- Stale lock reclaim: `locked_at < now - timeout_s * 2` resets to `queued`.
- Concurrency: semaphore of 2; CPU work inside agents goes through `asyncio.to_thread` (video stitcher, Pillow resize, ffmpeg subprocess).
- `worker_loop()` started in `main.py` lifespan when `settings.worker_enabled` (default true). Also runnable as `entrypoint.sh worker` for a separate process later.
- `/listings/{id}/approve` (`api/listings_workflow.py`) marks `await_review` done instead of signalling Temporal. `/retry` re-queues the failed step. `/cancel` marks remaining jobs `failed` and listing `CANCELLED`. `/pipeline-status` reads from `pipeline_jobs` (replaces the engagement cache hack).
- `agents/base.py`: remove `_safe_heartbeat`/`heartbeat_during`; `session_scope` unchanged. Agents no longer hold a transaction across provider calls: split into load -> call -> save where an agent awaits an external API (video, photo_analysis, content). Pattern: read what you need, exit the session, call the provider, open a new session to write.

### Removal
Delete `workflows/`, `activities/`, `temporal_client.py`, `temporalio` dep, Temporal env vars in `config/__init__.py`, `render.yaml`, `.env*.example`, compose. `DemoCleanupWorkflow` and `BaselineAggregationWorkflow` become plain functions run by a periodic task in the same worker loop (demo cleanup hourly; baseline weekly behind the learning flag). Fix the `storage=None` bug so R2 objects are deleted.

Tests: `tests/test_workflows/` replaced by `tests/test_pipeline/` covering enqueue, claim ordering, retry/backoff, failure marks listing FAILED, approve completes the gate, stale lock reclaim. Use the existing `postgres-test` DB.

## Phase 3: delete and flag (branch `chore/delete-and-flag`)

Delete outright:
- Agents: `cma_report.py`, `chapter.py`.
- Services: `market_tracker.py`, `idx_feed_poller.py`, `reso_adapter.py`, `comparables.py`, `property_scraper/` (Playwright), `scanner.py`, `drip_scheduler.py`, `tenant_bypass.py`, `feature_tags.py`, `engagement_score.py`, `api_keys.py`.
- API: `cma.py`, `launch.py`, `admin_providers.py` (routing admin), and the IDX/market pollers in `main.py` lifespan.
- Models: `cma_report.py`, `idx_feed_config.py`, `api_key.py` (with a drop migration `054_drop_cut_tables`).
- Providers: `google_vision.py`, `openai_vision.py`, `qwen.py`, `gemma.py`, `elevenlabs.py`, `kling.py`, `fallback.py`, `_routing.py`, `repliers.py`, `templates/`.
- Files: `structure.txt`, `railway.json`, `.vercel/`, `infra/`, root `vercel.json` (keep `frontend/vercel.json`), `CLOUD_MIGRATION_GUIDE.md`, `docs/PRE_LAUNCH_INFRA_CHECKLIST.md`, `docs/runbooks/cdk-deploy-recovery.md`, `docs/plans/`, `docs/superpowers/`, `docs/archive/`, session handoff docs, `TODO*.md`.
- Deps: `playwright`, `imagehash`, `passlib`, `clamd`, `temporalio`, all `opentelemetry-*`. Delete `telemetry.py` and the CloudWatch middleware; keep Sentry and call `init_sentry` from the worker path too.
- Frontend: `react-hotkeys-hook`, dead components (`grep -L` for imports under `src/components`), the S3-only `video-upload.tsx` key form.
- `providers/canva_generated/` (29.9k lines): replace with a thin httpx client covering only the endpoints `providers/canva.py` calls. Check which with `grep -n "canva_generated" src/`. If more than ~6 endpoints, keep the package and defer.

Feature flags (new `settings.features: set[str]`, env `FEATURES=`): `learning`, `health_score`, `performance_intelligence`, `help_agent`, `microsite`, `webhooks`, `listing_permissions`. Routers and pipeline steps register only when the flag is on. Default empty. Frontend hides the matching nav items when the `/settings/features` endpoint says off.

Update `MASTER_TODO.md`: replace with the phase list from this plan and their status.

## Phase 4: provider layer and photo analysis (branch `feat/claude-providers`)

### Providers (`src/listingjet/providers/`)
- `claude.py`: `ClaudeClient` on `anthropic.AsyncAnthropic`. Methods:
  - `complete_json(prompt, schema: type[BaseModel], *, model, system, max_tokens, temperature=None) -> BaseModel` using `client.messages.parse` with `output_config.format` (structured outputs). No regex fence stripping.
  - `analyze_images(image_urls: list[str], prompt, schema, *, model) -> BaseModel` using `image` blocks with `source.type = "url"` (R2 presigned URLs).
  - Records `response.usage` via `services/metrics.record_token_usage(agent, model, input, output)`; rates live in `config/ai_rates.py`, not hand-typed guesses.
  - Retries: SDK `max_retries=2`, no wrapper retry. Model IDs from settings: `claude_fast_model = "claude-haiku-4-5"`, `claude_quality_model = "claude-sonnet-5"`. Pin `anthropic>=1.0` and follow `/claude-api upgrade python` for the 0.x -> 1.x breaking changes (httpx2).
- `runway.py`: `RunwayClient.image_to_video(image_url, prompt, model, duration, ratio) -> task_id`, `poll(task_id) -> {status, url}`. Bearer key, `X-Runway-Version` header, async task polling with backoff. Models: `kling` (interiors), `veo3.1_fast` (exteriors). Confirm exact model enum against `https://docs.dev.runwayml.com/api/` at implementation time.
- `openai_images.py`: merge `_openai_edits.py`, `openai_staging.py`, `openai_dollhouse.py` into one client on the official `openai` SDK's `images.edit`.
- `mock.py`: keep; add `MockRunwayClient` and a mock `complete_json` that builds a schema instance from defaults.
- `factory.py` shrinks to `get_claude()`, `get_runway()`, `get_openai_images()`, `get_template_provider()`, each returning the mock when `use_mock_providers`.
- `base.py`: drop `VisionProvider`, `LLMProvider`, `VisionLabel`. Keep `TemplateProvider`, `VirtualStagingProvider` (now implemented by the OpenAI images client).

### Photo analysis agent (`agents/photo_analysis.py`, replaces `vision.py` + `photo_compliance.py`)
Schema `PhotoAnalysis(room: RoomLabel, is_interior, is_photo (false for floorplans/docs), quality: int 0-100, hero_score: int 0-100, features: list[str], is_empty_room, compliance: {people, signage, branding, text_overlay: bool}, notes: str)`. Room enum from `ROOM_LABEL_MAP` values plus `drone`, `entryway`, `primary_bedroom`, `primary_bathroom`, `floorplan`, `document`.

One Haiku 4.5 call per asset on the proxy URL, `asyncio.gather` under a semaphore of 8, 30 s per-image timeout, failures logged and skipped. Writes one `VisionResult` row per asset (`tier=1`, `model_used="claude-haiku-4-5"`, `raw_labels` holds the full schema dump). Add columns via migration `055_vision_result_analysis`: `is_empty_room bool`, `compliance jsonb`, `hero_score int`. Downstream readers (`packaging`, `video`, `content`, `floorplan`, `virtual_staging`, `image_edit` API) read from this single row. Delete the tier-2 query paths.

Compliance report shape returned by the step is unchanged so `review` UI keeps working.

### Floorplan (`agents/floorplan.py`)
Same prompt, moved to `analyze_images` on Sonnet 5 with the floorplan plus up to 5 room photos as real multi-image input, structured schema for the dollhouse scene JSON. `max_tokens` 8000.

### Virtual staging (`agents/virtual_staging.py`)
Only assets with `is_empty_room` are staged. Addon-gated as today.

Tests: `tests/test_agents/test_photo_analysis.py` with the mock client; provider tests use `pytest-httpx` (already a dev dep) for Runway; Claude client tested with a patched `messages.parse`.

## Phase 5: content and social (branch `feat/content-social`)

Merge `agents/content.py` and `agents/social_content.py` into `agents/content_social.py`, one Sonnet 5 call. Schema: `{mls_safe, marketing, instagram: {hooks[5], hashtags[20-30], cta}, facebook: {hooks[5], cta}, tiktok_caption}`. Inputs: metadata (PII-sanitised via `services/pii_filter.sanitize_for_prompt`), top features from photo analysis, brand-kit voice samples, tone intensity -> system prompt (keep `_tone_to_config`). `max_tokens` 8000. Context is passed once, not duplicated. FHA post-check via `services/fha_filter.fha_check`; on failure one retry with the FHA suffix, then keep whichever passes or the first with `fha_passed=False`. Writes `SocialContent` rows exactly as today so the social page keeps working.

## Phase 6: video (branch `feat/video-two-tier`)

### Baseline (`agents/video_baseline.py`)
- Input: packaged photos in MLS order from `PackageSelection`, capped at 10, non-photo assets excluded.
- ffmpeg per photo: `zoompan` Ken Burns 3 s at 1920x1080 (alternate zoom-in / pan directions), `xfade` 0.5 s between clips, end card from `services/endcard.py` appended, silent by default with an optional bundled royalty-free track under `assets/music/` mixed at -18 dB when `settings.video_music_enabled`.
- Runs in `asyncio.to_thread`; temp files cleaned. Upload to `videos/{listing_id}/tour.mp4`, upsert `VideoAsset(video_type="ai_generated" -> rename to "tour")`.
- Reuse `services/video_stitcher.py` for the concat; add the zoompan clip builder there.

### AI add-on (`agents/video_ai.py`)
- Picks up to 6 shots: 1 best exterior, 1 drone if any, 4 interiors in `WALKTHROUGH_ORDER` (keep `video_template.py` room prompts, drop Kling-specific camera controls and `NEGATIVE_PROMPT`).
- Per shot: `runway.image_to_video(model = "veo3.1_fast" if exterior/drone else "kling", duration=5, ratio="1280:720")`. Task IDs stored in `VideoAsset.metadata_["runway_tasks"][asset_id]` immediately, so a retry polls existing tasks instead of resubmitting. Semaphore 3.
- Failed shots fall back to a Ken Burns clip of the same photo so the tour is always complete. Stitch with the same builder; replaces the baseline `tour.mp4`.
- Cost recorded per second generated using rates in `config/ai_rates.py`.
- Gated by addon `ai_video_tour` for every billing model (no legacy default).

### Social cuts (`agents/social_cuts.py`)
Unchanged ffmpeg crops, moved to `asyncio.to_thread`. Chapters: derived list of `{room, start_s, end_s}` from the clip manifest, stored on `VideoAsset.metadata_["chapters"]`; `video-player.tsx` already reads chapters.

Tests: stitcher unit tests with tiny generated PNGs (ffmpeg present in CI via `apt-get`), remove the two real `asyncio.sleep(3)` tests, Runway resume-from-task-ids test.

## Phase 7: frontend, CI, hosting config (branch `feat/frontend-ci-hosting`)

- `frontend/src/app/listings/[id]/page.tsx`: replace the 5 s `setInterval` with `lib/use-listing-events.ts` (SSE from `/sse`), poll only as fallback when SSE disconnects. `pipeline-progress.tsx` reads the new `/pipeline-status` shape (job list with status/error).
- Retry button on a FAILED listing calls `/retry`; error text shown from the failed job.
- `.github/workflows/test.yml`: single backend job (ffmpeg installed, Postgres service) plus a frontend job running `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npx vitest run`, `npm run build`. Delete the duplicate test block in `deploy.yml`; `docker.yml` builds on PRs, no push. Remove `|| true` on audits or drop the audits.
- `render.yaml`: one free web service, `worker_enabled=true`, env group without Temporal keys; `preDeployCommand` keeps migrations. `docker-compose.yml` trimmed to postgres, postgres-test, redis, api.
- `Dockerfile`: no Playwright; `ffmpeg`, `libpq5` only; pin deps via `uv.lock` (untrack from `.gitignore`, build with `uv sync --frozen`).
- `.env.example` regenerated from `Settings` fields (script `scripts/gen_env_example.py`).
- `justfile`: `just check` (ruff, `pytest -m "not db"`), `just test`, `just dev`. Add `db` marker to tests that need Postgres.

## Phase 8: docs (branch `docs/rewrite-claude-md`)

- `CLAUDE.md` rewritten under 100 lines: stack, branching, `just` commands, pipeline definition location, feature flags, migration head, free-tier gotchas (Supabase pause, Render spin-down).
- `README.md` architecture section updated (no Temporal, no AWS).
- `PROJECT_OVERVIEW_FOR_LLM.md` refreshed or deleted in favour of CLAUDE.md.
- `docs/runbooks/free-tier-setup.md`: account creation checklist and env values (replaces `render-supabase-cutover.md` and `r2-cutover.md`).

## Operational steps the user does

1. Create Supabase project (US West), a `listingjet` role with `BYPASSRLS=false`, copy pooler + direct URLs.
2. Create Upstash Redis, copy `rediss://` URL.
3. Create R2 bucket `listingjet-media`, enable public bucket domain, create an API token.
4. Render: new web service from repo Docker, free plan, env group values.
5. Vercel: import `frontend/`, set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_MEDIA_HOST`.
6. Runway dev portal: org + $10 credits, API key. Anthropic and OpenAI keys.
7. Resend key, Sentry DSN (optional).

## Verification

Per phase, in order:
- `just check` green (ruff + non-DB tests under 30 s), `just test` green with Postgres up.
- Phase 2: `scripts/seed_sample_listing.py` creates a tenant, user, listing with 12 sample photos from `tests/fixtures/photos/`; run the worker with `USE_MOCK_PROVIDERS=true`; watch `pipeline_jobs` progress to `distribution` done; approve via API; confirm `Listing.state == DELIVERED`. Kill the worker mid-step and restart; confirm the job is reclaimed. Force an agent exception; confirm listing `FAILED` with error and that `/retry` recovers.
- Phase 4-6: same seed with real keys, one listing, budget noted in the PR (expected under $1 without the video add-on, under $5 with it). Check `record_token_usage` rows match `response.usage`.
- Phase 7: `npm run build` passes; in the browser (Playwright MCP or Chrome), upload photos through the wizard, watch SSE-driven progress without polling in the network tab, approve, download the MLS bundle, play the tour video, view social captions.
- Deploy: Render service healthy at `/health/deep`, Vercel preview loads listings with R2 images, one end-to-end listing run on the deployed stack.

## Out of scope for this pass

Temporal self-hosting, tenant model routing, Higgsfield integration, React Query migration, server-component conversion of marketing pages, XGBoost, cross-tenant sharing repair, Vercel Pro.
