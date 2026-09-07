# Phase 8: Docs Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The repo's onboarding docs describe the system that exists after Phases 1–7 — one Render web service with an in-process worker polling a Postgres job table, Claude + OpenAI images + Runway + Canva providers, free-tier hosting — and nothing else. `CLAUDE.md` fits in 100 lines; `README.md` has a truthful architecture section; a single free-tier setup runbook replaces the AWS-era cutover runbooks; stale planning docs are gone.

**Architecture:** Documentation only. No code changes except a tiny link-check script under `scripts/`.

**Tech Stack:** Markdown; `scripts/check_doc_links.py` (stdlib only).

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` — "Phase 8: docs" and "Operational steps the user does".

## Global Constraints

- Branch `docs/rewrite-claude-md` off `feat/frontend-ci-hosting` (PR #312). PR targets `feat/frontend-ci-hosting`. Never push to `main`; never merge; never amend published commits.
- Every fact in the docs must be verifiable against the tree at HEAD: step names from `src/listingjet/pipeline/definition.py` (21 steps), agents from `src/listingjet/agents/`, routers from `src/listingjet/main.py`, settings from `.env.example` (generated), migration head `056_video_asset_metadata`, test count from the last full run (903 passed), CI shape from `.github/workflows/`. No numbers or names from memory.
- `CLAUDE.md` ≤ 100 lines (`wc -l`), no tables wider than 100 chars, no duplicated content with `README.md` (CLAUDE.md is for agents working in the repo; README is for humans evaluating or running it).
- No em-dash-heavy prose; plain sentences. Commands in fenced blocks. Relative links only, and every relative link must resolve (`scripts/check_doc_links.py`).
- Every Bash call passes an explicit timeout.
- Commit trailer on every commit:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

---

## File map

| File | Action |
|---|---|
| `CLAUDE.md` | rewrite ≤ 100 lines |
| `README.md` | rewrite Architecture, Agent Pipeline, Tech Stack, Quick Start, Running Tests, Project Structure, Contributing; drop the Lint badge |
| `PROJECT_OVERVIEW_FOR_LLM.md` | delete (CLAUDE.md is the agent-facing overview) |
| `docs/runbooks/free-tier-setup.md` | create |
| `docs/runbooks/render-supabase-cutover.md`, `docs/runbooks/r2-cutover.md` | delete |
| `docs/runbooks/secret-rotation.md` | update key list (drop `KLING_*`, `GOOGLE_VISION_API_KEY`; add `RUNWAY_API_KEY`, `GOOGLE_API_KEY`, `CANVA_*`) |
| `docs/AI-Models-Overview.md` (Qwen/Gemma, deleted in Phase 3), `docs/PROXY-IMAGE-PIPELINE.md` (planned feature that shipped: `Asset.proxy_path`) | delete |
| `docs/superpowers/plans/*`, `docs/superpowers/specs/*`, `docs/reviews/*` | keep (history) |
| `MASTER_TODO.md` | Phase 7 row `#312`; Phase 8 row; carried list pruned to what is still open |
| `scripts/check_doc_links.py` | create (walk `*.md` outside `node_modules`/`.venv`, resolve relative links, exit 1 on a miss) |

---

### Task 1: `CLAUDE.md`, `README.md`, runbooks, deletions (one writer, one voice)

**Files:** as in the file map (all except `MASTER_TODO.md`, which Task 2 finalises).

**Interfaces:**
- Consumes: facts from the tree (see Global Constraints). Existing `CLAUDE.md` sections that are still true and must survive in condensed form: branching rules, explicit Bash timeouts, `just` targets + Windows equivalents, generated `.env.example`, CI shape, key file locations, package naming note (`launchlens` dir vs `listingjet` package), migration head, `FEATURES` flags, route mounting incl. the `/sse` exception, the stop-hook note.
- Produces: the four documents below.

- [ ] **Step 1: `CLAUDE.md`** — target structure (≤ 100 lines):
  1. Title + one-paragraph "what this is" (21-step pipeline, in-process worker, job table).
  2. **Stack** (4 bullets: backend, frontend, hosting, tests).
  3. **Branching and PRs** (fresh branch per task, push, PR, no merge without green light, never push `main`, never amend published commits, `gh pr create` works).
  4. **Working rules** (explicit Bash timeout on every call; commit + push before ending a session because of the stop hook; `.env.example` is generated, never hand-edit; run `just env-check`).
  5. **Commands** — one fenced block: `just check|test|dev|worker|env-check` and the Windows equivalents (three lines: ruff, pytest, uvicorn/worker via `.venv/Scripts/python.exe -m ...`).
  6. **CI** (3 sentences: `test.yml` backend + frontend jobs; `deploy.yml` Render hook on `main`; `docker.yml` builds on PRs).
  7. **Where things live** — one compact table, ≤ 14 rows: `main.py`, `pipeline/definition.py` (the pipeline: `Step(...)` list and gates), `pipeline/runner.py`, `pipeline/worker.py`, `agents/`, `providers/` (Claude text+vision, OpenAI images, Runway video, Canva; `mock.py` when `USE_MOCK_PROVIDERS=true`), `api/`, `models/`, `services/`, `features.py`, `config/` (`Settings`, `ai_rates.py`, `tiers.py`), `alembic/versions/`, `tests/`, `frontend/src/` (App Router; `lib/generated/api.d.ts` regenerated via `npm run generate-api`), `scripts/`.
  8. **Constraints and gotchas** — bullets: migration head 056 (`056_video_asset_metadata`); `FEATURES=` list of seven flags, off by default, restart to change; routes mounted at their prefix, no `/v1`, SSE at `/sse/listings/{id}/events` with `?token=`; worker runs in-process (`WORKER_ENABLED`), no separate worker service; Render free tier sleeps when idle (worker and hourly watchdog pause with it); Supabase free pauses after 7 idle days; ffmpeg required (`FFMPEG_BIN`); mock providers make every photo a real photo (`is_photo=True`, quality 85); package naming note.
  9. **Docs** — three links: `README.md`, `docs/runbooks/free-tier-setup.md`, `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md`, `MASTER_TODO.md`.
- [ ] **Step 2: `README.md`** — keep the tagline and CI badge (drop the Lint badge; `lint.yml` is gone). Replace the ASCII architecture diagram with an accurate one: Next.js on Vercel → FastAPI on Render (API + in-process worker) → Supabase Postgres (RLS, `pipeline_jobs`) + Upstash Redis (rate limits, revocation) + Cloudflare R2 (media); providers: Anthropic Claude (Haiku 4.5 per photo, Sonnet 5 copy/floorplan), OpenAI images (staging, edits, dollhouse), Runway (`gen4_turbo` / `veo3.1_fast`), Canva (flyers), Resend (email), Stripe, Sentry. Replace "Agent Pipeline (15 agents)" with **Pipeline (21 steps)**: a table `step | needs | what it does | gate` generated from `definition.py` (pre-review: ingestion, photo_analysis, property_verification (optional), coverage, virtual_staging (add-on), floorplan, dollhouse_render (optional), packaging, video_baseline (optional); gate: await_review; post-review: video_ai (add-on `ai_video_tour`), content_social, brand (optional), social_cuts (optional), mls_export, distribution; feature-flagged: microsite, learning, social_event, health_score, performance_intelligence). Tech Stack table updated (no Google Vision, no GPT-4V, no Kling, no Claude 3; tests "900+ pytest, vitest"; CI "GitHub Actions: test (backend + frontend), docker build"). Quick Start: prerequisites (Python 3.12, Node 22, Postgres 16 or Docker, ffmpeg), `cp .env.example .env` with the minimum keys (`DATABASE_URL`, `DATABASE_URL_SYNC`, `JWT_SECRET`, `REDIS_URL` optional for dev?, `USE_MOCK_PROVIDERS=true`, `FFMPEG_BIN` if needed), `just dev` (worker runs in-process), frontend `npm ci && npm run dev` with `NEXT_PUBLIC_API_URL=http://localhost:8000`, `docker-compose up` alternative; Running Tests (`just test`, needs the test DB on 5433 — `docker-compose up postgres-test` or the local cluster; `just check` for the fast subset). Project Structure block updated (no `config.py` — it is `config/`; `alembic/versions/` 001→056; `scripts/`). Contributing: `just check`, `just test`, frontend `npm run lint && npx tsc --noEmit && npx vitest run`.
- [ ] **Step 3: `docs/runbooks/free-tier-setup.md`** — sections: Overview (what runs where, cost: $0 hosting + AI usage); **Accounts** checklist in order: Supabase (project, region, `listingjet` role with `BYPASSRLS=false`, pooler URL for `DATABASE_URL` + `DB_USE_PGBOUNCER=true`, direct URL for `DATABASE_URL_SYNC`), Upstash (Redis, `rediss://`), Cloudflare R2 (bucket `listingjet-media`, public bucket domain → `NEXT_PUBLIC_MEDIA_HOST`, API token → `S3_*`, `S3_ENDPOINT_URL`, `AWS_REGION=auto`), Render (Blueprint from `render.yaml`, free plan, env group `listingjet-shared`, `WORKER_ENABLED=true`, deploy hook URL → GitHub secret `RENDER_DEPLOY_HOOK_URL` — check the exact secret name in `.github/workflows/deploy.yml`), Vercel (import `frontend/`, Hobby, `NEXT_PUBLIC_API_URL=/api` + rewrite in `frontend/vercel.json` to the Render URL, `NEXT_PUBLIC_MEDIA_HOST`), Anthropic + OpenAI keys, Runway (dev portal, $10 credits, `RUNWAY_API_KEY`), Resend (`RESEND_API_KEY`, `EMAIL_ENABLED=true`), Sentry (optional), Stripe (test keys; optional for testing), Canva (optional). **Environment values** table: every key in `render.yaml`'s env group with where it comes from (cross-check `.env.example`). **First deploy**: push to `main` → `deploy.yml` → Render runs `preDeployCommand` migrations → `/health/deep`; seed with `scripts/seed_sample_listing.py` against the deployed DB or via the UI wizard. **Smoke test**: upload photos, watch `/sse/listings/{id}/events`, approve, download bundle, play tour. **Free-tier gotchas**: Render sleeps after 15 min idle (first request ~30 s; worker + hourly watchdog paused; optional external cron ping to `/health` on test days), Supabase pauses after 7 idle days (restore from dashboard), Upstash command quota vs per-request revocation `EXISTS`, R2 egress free, Runway URLs expire in 24–48 h (we download immediately), Vercel Hobby is non-commercial. **Rotating secrets**: link to `secret-rotation.md`.
- [ ] **Step 4: `secret-rotation.md`** — replace the `GOOGLE_VISION_API_KEY` and `KLING_*` subsections with `GOOGLE_API_KEY` (Drive link import) and `RUNWAY_API_KEY`; add `CANVA_API_KEY`/`CANVA_CLIENT_SECRET` if absent; fix any AWS/ECS mention to Render env group.
- [ ] **Step 5: deletions** — `PROJECT_OVERVIEW_FOR_LLM.md`, the two cutover runbooks, `docs/AI-Models-Overview.md`, `docs/PROXY-IMAGE-PIPELINE.md`. Grep the tree for references to the deleted files (`grep -rn "PROJECT_OVERVIEW_FOR_LLM\|render-supabase-cutover\|r2-cutover\|AI-Models-Overview\|PROXY-IMAGE-PIPELINE" --include=*.md --include=*.yaml --include=*.py --include=*.ts .`) and fix each (e.g. the comment in `render.yaml`).
- [ ] **Step 6: gates** — `wc -l CLAUDE.md` ≤ 100; `scripts/check_doc_links.py` (write it: ≤ 60 lines, stdlib, regex `\[[^\]]*\]\(([^)#]+)(#[^)]*)?\)`, skip `http(s)://`, `mailto:`, resolve relative to the file, report misses, exit 1) passes; a fact check script-free: for each step name in the README table, `grep -c "Step(\"<name>\"" src/listingjet/pipeline/definition.py` = 1 (the implementer runs this loop and pastes the output in the report).
- [ ] **Step 7: commit** — `docs: rewrite CLAUDE.md and README for the free-tier architecture; free-tier setup runbook`.

---

### Task 2: `MASTER_TODO.md`, verification, PR

- [ ] `MASTER_TODO.md`: Phase 7 row `#312`; Phase 8 row `docs/rewrite-claude-md` / PR # / "done, awaiting merge"; add a "Merge order" line `#306 → #307 → #308 → #309 → #310 → #311 → #312 → #313`; carried list pruned to: real-provider run pending keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `RUNWAY_API_KEY`); ops account setup (link to the runbook); `GOOGLE_VISION_API_KEY` → `GOOGLE_API_KEY` move; Runway has no Kling; frontend lint warnings (79) and SSE hook reconnect backoff; `pii_filter` list recursion; SSE ticket instead of JWT in query string; post-timeout watchdog nuance (deferred jobs). Remove everything that is done.
- [ ] Verification: run every command in `CLAUDE.md`'s Commands block on this machine using the Windows equivalents (`ruff`, `pytest -m "not db and not ffmpeg" -q`, `gen_env_example.py --check`; start `uvicorn` in the background and hit `/health`, then kill it; `python -m listingjet.pipeline.worker` starts and is killed after 5 s) and record results. Run `scripts/check_doc_links.py`. `wc -l CLAUDE.md`.
- [ ] Commit `docs: master todo for phase 8; doc link check`, push `docs/rewrite-claude-md`, `gh pr create --base feat/frontend-ci-hosting --title "docs: rewrite CLAUDE.md, README, free-tier setup runbook (phase 8)"` with body: what changed per file, what was deleted and why, verification (line count, link check, commands run), merge order. End with the attribution lines. Then `docs: link phase 8 PR` commit with the number. Do not merge.

---

## Self-review

- **Spec coverage:** CLAUDE.md < 100 lines with stack/branching/just/pipeline location/flags/head/free-tier gotchas ✔ T1; README architecture no Temporal/AWS ✔ T1; PROJECT_OVERVIEW deleted ✔ T1; `free-tier-setup.md` replaces the two cutover runbooks ✔ T1; operational steps from the spec land in the runbook ✔ T1.
- **Placeholders:** none. **Type consistency:** script name `scripts/check_doc_links.py` in T1 and T2.
