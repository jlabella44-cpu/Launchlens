# ListingJet efficiency and cost review

Date: 2026-09-01. Scope: whole repo at commit `74175e3`. Method: six parallel reviewers (AI usage, Temporal pipeline, backend, frontend, infra/cost, tests/CI/dev loop), with the highest-impact claims re-verified by hand. File and line references are to that commit.

## 1. Verdict

The core product path (upload, vision, packaging, review, copy, export) is roughly a third of the code. The rest is speculative features with no customers, dead modules, a 30k-line vendored Canva SDK, and 30k lines of checked-in AI planning documents. The codebase is heavier than the product.

Money leaves in three places, in this order:

1. **Kling video.** Every non-credit listing generates exactly 12 pro clips, padding with repeated photos when fewer qualify, and a Temporal retry regenerates all 12 because clip IDs are never persisted.
2. **Per-photo GPT-4o, twice.** Tier-2 vision and photo compliance each call GPT-4o on largely the same photos. Compliance sends full-resolution originals although a 1024px proxy exists.
3. **Image generation.** Virtual staging runs up to 8 `gpt-image-1.5` edits on every interior room with no check that the room is empty.

Hosting is small next to that, but Temporal Cloud is the largest fixed monthly line and the pipeline uses almost none of what Temporal offers.

Several findings are not efficiency issues but bugs that must be fixed first: refresh tokens are accepted as access tokens, uploads have no size or type limits, ChapterAgent fails on every real run, Playwright is almost certainly broken in the Docker image, and the frontend CI job runs no lint, typecheck, tests, or build.

## 2. Where the money goes per listing

Assumptions: ~40 photos uploaded, 25 packaged, 1 floorplan, default routing (Claude text, Google Vision tier 1, OpenAI tier 2), legacy billing.

| Step | Calls today | Model | Waste |
|---|---|---|---|
| Vision tier 1 | ~40 | Google Vision labels | Sequential, one per photo, no heartbeat |
| Vision tier 2 | ~20 | gpt-4o | Same photos rescanned by compliance |
| Photo compliance | ~25 | gpt-4o | Full-res originals; results not persisted, so `/image-edit` rescans |
| Floorplan | 1 to 2 | gpt-4o | Multi-image prompt but only the first image is sent on the default provider |
| Dollhouse | 1 | gpt-image-1.5 | Fine |
| Virtual staging | 0 to 8 | gpt-image-1.5 | No emptiness check; furnished rooms get staged |
| Copy + social + CMA | 2 to 4 | claude-sonnet-4-6 | Context JSON duplicated in prompt; max_tokens 1024 truncates social output |
| Video | 12 clips | kling v2.5 pro | Always 12; padded; retries regenerate all |
| Chapters | 1 | gpt-4o | Sends an S3 key, not a URL; fails every time, still records cost |

The cost-recording layer cannot tell you any of this: Claude usage is never recorded, Qwen and Gemma are double-counted, OpenAI vision records nothing, and the admin "rate card" is hand-typed guesses in `services/metrics.py:15-34`.

## 3. AI strategy for 2026

The provider layer was built for a 2025 world (three interchangeable text LLMs, regex JSON parsing, no caching). What to change:

- **Model.** `claude-sonnet-4-6` is pinned in `providers/claude.py:16` and `services/help_agent.py:21`. Sonnet 5 is cheaper per token and newer. Haiku 4.5 is the right tier for per-photo classification. Verify current pricing before switching; the figures the reviewers had (cached June 2026) were Sonnet 5 at $2/$10 per million tokens against Sonnet 4.6 at $3/$15.
- **Structured outputs.** Every JSON-returning call uses "return only JSON" plus regex fence stripping in `agents/base.py:48-74`. Claude supports `output_config.format` and OpenAI supports `response_format`. This removes the entire class of "empty or invalid LLM JSON" fixes (#283) and the FHA re-call loops.
- **max_tokens.** 1024 in all three text providers, while social content asks for 10 captions plus 30 hashtags. Raise per call site (social and floorplan need 4k or more).
- **Prompt caching.** Zero `cache_control` in the repo. Pipeline prompts are too short to matter. The help agent resends a large system prompt and 15 tool definitions up to 5 times per message; cache those.
- **One multimodal pass per photo.** Replace Google Vision plus GPT-4o tier 2 plus GPT-4o compliance with one call per photo returning room, quality, hero, and compliance fields in one schema. That takes ~85 vision calls per listing to ~25.
- **Merge content and social** into one call. They share metadata, vision features, and FHA constraints.
- **Batch API** for anything not user-facing (learning, backfills, rescoring) at half price.
- **SDK.** `anthropic` 0.87 is locked; 1.x exists and the upgrade has breaking changes (httpx2). Plan it.
- **Collapse the routing layer.** `_routing.py`, `factory.py`, and `fallback.py` support per-agent and per-tenant routing, but no caller passes `agent=` or `tenant_id`, so tenant routing is unreachable. ElevenLabs, `FallbackVisionProvider`, the HTML templates under `providers/templates/`, and Kling camera controls are dead. Keep two providers (Claude text, one vision) and delete the rest.
- **Retry stacking.** Provider retry x3, then `FallbackLLMProvider` catches any exception including 4xx and pays again on Claude, then Temporal x3. Worst case 12 paid completions for one call. Retry only on transient errors and cap total attempts.

## 4. Pipeline and Temporal

- The workflow (`workflows/listing_pipeline.py:78-297`) is 22 activities, mostly serial. Floorplan, tier 2, and coverage could run together. Eleven post-approval steps run serially after the user is already marked delivered; five of them are ~100ms DB writes that do not deserve a Temporal round trip.
- Inside activities, tier 1 and tier 2 vision loop `await` one photo at a time (`agents/vision.py:126-148`, `:194-236`). A `gather` with a semaphore of 8 is a one-line change.
- **The stuck-state bugs (#278, #281, #282, #284) were patched, not fixed.** Nothing in the workflow ever writes `FAILED` or `PIPELINE_TIMEOUT`. When a required activity exhausts retries, the listing row sits in `ANALYZING` or `EXPORTING` forever. Fix: a try/except around `run()` that calls a `mark_failed` activity, plus an `execution_timeout` on `start_workflow`.
- Approval commits `APPROVED` then signals Temporal inside a swallowing try/except (`api/listings_workflow.py:97-117`). A lost signal is a permanent hang with no reconciliation.
- One retry policy for everything (`maximum_attempts=3`, no non-retryable types, no schedule-to-close). `ValueError("Listing not found")` is retried three times. Video can block approval for 90 minutes because the `gather` at line 183 couples review to the video job.
- Emails, Canva renders, S3 uploads, and Kling jobs are non-idempotent and sit inside retried activities. Users get duplicate "listing delivered" emails.
- `subprocess.run(ffmpeg)` and Pillow calls run synchronously inside `async def` activities on a single event loop. One stitch freezes heartbeats and every other activity on the worker. Move CPU work to `asyncio.to_thread` or a second task queue, and set `max_concurrent_activities` explicitly (default is 100 on a 512MB box).
- `TemporalClient.cancel_workflow()` described in CLAUDE.md does not exist; `/cancel` never cancels the workflow. `DemoCleanupWorkflow` passes `storage=None`, so R2 objects are never deleted.
- Three scheduling mechanisms coexist: Temporal schedules, in-process asyncio loops in the API lifespan, and nothing at all for the drip scheduler (dead code). The IDX and market pollers have no lock and double-run on two API replicas.

**Temporal verdict.** Not justified at today's volume. The workload is N listings per day, ~20 mostly independent steps, one human gate, one long external job. That is a Postgres job table with `SELECT ... FOR UPDATE SKIP LOCKED` (the outbox poller already uses the pattern) and a small worker. Migration is about a week because the agents are already clean `execute(ctx)` functions. If you keep Temporal, self-host it on a Render private service until volume justifies Cloud, and actually use child workflows, heartbeat resume, and workflow tests. Either way, decide before building more on `ListingState`.

## 5. Backend

- 42 routers (9.2k lines), 47 services (7.6k), 25 agents (4.5k), 51 migrations. `providers/canva_generated/` is 29.9k lines, larger than the application. Move it to a build-time artifact or replace with a thin httpx client for the handful of endpoints used.
- **Security, fix this week:**
  - `api/deps.py:38` and `middleware/tenant.py:35` decode JWTs without checking `type == "access"`. A 7-day refresh token works as a bearer everywhere.
  - Token revocation fails open and opens a fresh Redis connection per request (`services/auth.py:104-108`).
  - Presigned uploads have no content-length ceiling and no type check; ClamAV is configured but never called and does not exist on Render.
  - CORS allows credentials for any `listingjet*.vercel.app` origin (`main.py:161`).
  - `canva_oauth.py:122` decodes the Canva JWT without signature verification.
  - `TRUSTED_PROXY_COUNT = 0` hardcoded, so behind Render all unauthenticated users share one rate-limit bucket.
  - Auth lockout failures are swallowed (`api/auth.py:151,167,176`), silently disabling brute-force protection.
  - `field_encryption.encrypt()` returns plaintext when no key is configured. Raise in production.
- Redis clients are constructed ad hoc in 8 places, all sync, all from async code. Use one `redis.asyncio` client on `app.state`.
- Every agent holds a DB transaction open for its whole runtime, including LLM calls and Kling polling. Under Supabase's transaction pooler that pins a connection for up to 30 minutes per activity.
- Missing indexes on `users.tenant_id`, `events.tenant_id`, `outbox.tenant_id`, `audit_logs.tenant_id`, and all 8 FKs in `listing_permission.py`. Every RLS policy filters on `tenant_id`.
- The cross-tenant listing permissions feature cannot work under the RLS policy added in migration 051; grantees always 404. Tests pass because they run without RLS.
- `GET` requests auto-commit (`database.py:47`); `get_db_admin` never commits.
- 74 `except: pass` blocks. Ruff runs only E, F, I, W. Enabling B, UP, ASYNC, S, SIM, RUF surfaces 676 findings, most real.

**Feature bloat.** About 6,500 lines can be cut or deferred without touching the core path:

| Feature | Verdict | Why |
|---|---|---|
| CMA reports, market tracker, IDX/RESO poller | Cut | Need ATTOM/RESO keys; superadmin-only or no UI; poller starts at boot |
| Learning / weight manager, baseline aggregation | Cut | ML on zero rows; XGBoost is not even a dependency |
| Listing permissions / cross-tenant sharing | Cut | Broken under RLS |
| Tenant bypass, feature tags, engagement score, drip scheduler, API keys, `api/launch.py` | Cut | No callers or no UI |
| Health score, performance intelligence, help agent, microsite, webhooks | Defer | ~3,800 lines waiting on outcome data or customers |
| Team invites, FHA/PII filters | Keep | Small, real |

## 6. Frontend

- 29 pages, 11.3k lines under `app/`. "use client" on 94 of 111 files and 25 of 29 pages, including the marketing landing page and static FAQ/support text, which ship React plus framer-motion for fades that CSS handles.
- Every page fetches client-side with `useEffect`. No React Query or SWR, no `loading.tsx` or `error.tsx`, no server-side fetching.
- Six independent polling intervals. The listing detail page polls every 5 seconds firing 3 to 5 requests per tick. An SSE hook (`lib/use-listing-events.ts`) exists with zero consumers and the backend serves `/sse`. Wire it and delete the poll.
- Three separate upload implementations totalling ~1,350 lines.
- The typed API client is theatre: `openapi-fetch` handles 8 calls, the other ~137 go through an untyped `this.request()`, and `lib/types.ts` hand-maintains 82 interfaces. The committed OpenAPI spec has 89 paths; the backend mounts 156. Regenerate in CI and fail on drift, or drop the generated pair.
- `next.config.ts` allows only `*.s3.amazonaws.com` image hosts. After the R2 cutover `next/image` will reject every listing image. Fix before the DNS flip.
- Two conflicting `vercel.json` files. `react-hotkeys-hook` has zero imports. ~580 lines of dead components. `DollhouseViewer` in CLAUDE.md does not exist.
- ~4,000 lines of pre-launch routes (admin, review queue, team, analytics, health, changelog, support) that could sit behind a flag.
- CI runs no eslint, `tsc`, vitest, or `next build`. Four vitest files, ~170 lines. Ten Playwright specs run nowhere.

## 7. Infra and hosting

- **Docker.** `Dockerfile:33` installs Playwright and Chromium into the runtime stage as root, after the multi-stage copy, for both the API and worker images. The browser lands in `/root/.cache/ms-playwright`, then `USER listingjet` switches away with no `PLAYWRIGHT_BROWSERS_PATH`. The only consumer swallows exceptions, so you ship Chromium and get silent scrape failures. Split into an API image (slim, libpq) and a worker image (ffmpeg, optionally Chromium), or drop Playwright.
- `uv.lock` is both tracked and in `.gitignore`, and the Docker build ignores it, so production resolves fresh from version floors on every deploy. Build with `uv sync --frozen`.
- **Sizing.** Both services are on Render `starter`. The old checklist recorded the worker needing 2 vCPU / 4GB. The worker reads whole MP4s into memory, runs ffmpeg and LANCZOS resizes of 50MB originals, and has no concurrency cap. Put the API on the smallest plan and the worker on a 2GB-class plan with `max_concurrent_activities=2`.
- **Four observability stacks.** CloudWatch (now a no-op middleware still executed per request), OpenTelemetry with no collector in prod (6 packages plus grpcio for nothing), Sentry, and JSON logs. Keep Sentry and add `init_sentry` to the worker, which never calls it today.
- **Rate limiter fails closed.** Redis unavailable or Upstash quota exhausted means 503 on every request (`middleware/rate_limit.py:85`).
- **Dead dependencies.** `imagehash` (zero imports; pulls numpy, scipy, PyWavelets), `passlib` (code imports `bcrypt` directly), three OTel instrumentation packages, `clamd`.
- **Dead files.** `railway.json`, `.vercel/project.json`, `structure.txt` (3.2MB UTF-16 Windows tree dump that lists `.env` and is 66% of the git pack), `infra/` CDK, `CLOUD_MIGRATION_GUIDE.md`, `PRE_LAUNCH_INFRA_CHECKLIST.md`, docker-compose services that do not exist in prod (ClamAV, Jaeger, PgBouncer, a second Postgres).
- Settings has 106 fields; several are never read. `.env.example` says `LLM_PROVIDER=anthropic` but the code expects `claude`.
- Temporal Cloud has no free tier and is the largest fixed line. Vercel Hobby is not licensed for commercial use.

## 8. Tests, CI, and the dev loop

- **The suite works**: 883 passed, 3 skipped, 0 failed in 165 seconds with Postgres up. System Python is 3.11 while the project requires 3.12, so the documented install command fails cold.
- 36 of those seconds are two video tests that hit a real `asyncio.sleep(3)` stagger. API tests cost ~1 second each because bcrypt runs at production cost with no test override. There is no marker to run the 484 tests that do not need Postgres.
- `fail_under = 60` is decorative: `pytest-cov` is not installed and CI never runs coverage.
- **CI.** Tests run twice on every push to main (`test.yml` and a drifted copy in `deploy.yml`). `docker.yml` builds on main only with `push: false`, pure spend. `pip-audit || true` and `npm audit || true` cannot fail. No Trivy, no semantic-release, no `.releaserc.json`, no `dependabot.yml`, no tags, despite CLAUDE.md claiming all of them.
- **Docs.** ~85% of documentation lines are executed AI session plans (`docs/plans/`, `docs/superpowers/`, handoffs). CLAUDE.md is wrong about the migration head (051, not 050), the agent count, LocalStack, Trivy, semantic-release, pytest-cov, and `DollhouseViewer`.
- **AI-dev readiness.** No `.claude/` directory, no hooks, no skills, no `justfile`, no pyright or mypy, no single verification command. CLAUDE.md depends on a stop hook that lives outside the repo.

## 9. Thirty-day plan

**Week 1: stop the bleeding.**
- Auth: enforce `type == "access"`; fail closed on revocation. Upload size and type limits. CORS origin list. Verify the Canva JWT.
- Video: clip count = min(12, distinct qualifying photos); gate on the add-on for all billing models; persist Kling task IDs so retries resume instead of regenerating.
- Workflow: try/except around `run()` writing `FAILED`; `execution_timeout`; non-retryable `ValueError`; decouple review from video.
- Fix `next.config.ts` for R2 and the Playwright path (or drop it).

**Week 2: delete.**
- `structure.txt`, `railway.json`, `.vercel/`, `infra/`, superseded docs, `docs/plans`, `docs/superpowers`, dead services (~900 lines), dead providers, dead frontend components, `react-hotkeys-hook`, `imagehash`, `passlib`, OTel and CloudWatch code paths.
- Cut the features in the "Cut" row. Flag the "Defer" row.
- Rewrite CLAUDE.md to what is true, under 100 lines.

**Week 3: make verification real.**
- `justfile` with `just check` (ruff, pyright, non-DB tests, under 30 seconds) and `just test`. Mark DB tests. Patch the sleeps and bcrypt rounds in tests.
- CI: single test job, frontend lint plus `tsc` plus vitest plus `next build`, Docker build on PRs, coverage enforced or the gate removed.
- `.claude/settings.json` with ruff-on-edit and check-on-stop hooks; skills for new migration, new agent, new endpoint.
- Tighten ruff; add pyright basic.

**Week 4: consolidate the AI calls.**
- Structured outputs on every JSON call; raise `max_tokens`; drop duplicated context.
- Merge tier 2 and compliance into one call per photo on the proxy image; persist results.
- Staging emptiness check.
- Record real token usage from `response.usage`; move rates to config.
- Evaluate Sonnet 5 and Haiku 4.5 on the copy and classification paths respectively.
- Then decide: self-host Temporal, or migrate to a job table.

## 10. Decisions only you can make

1. Keep Temporal (self-hosted) or move to a Postgres job table.
2. Which "Cut" features you are willing to actually delete versus flag.
3. Whether video stays a default for legacy-billing listings or becomes an add-on everywhere.
4. Vercel Pro versus moving the frontend to Render or Cloudflare Pages.
