# Phase 7: Frontend live updates, CI, hosting config — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The listing page follows the pipeline live over SSE (polling only as fallback), shows failed-step errors with a working Retry, and the repo's CI, Docker, Render, compose, env example and dev commands match the free-tier single-service architecture. Two carried pipeline gaps close: add-ons bought after enqueue re-run their step, and stuck listings time out.

**Architecture:** Frontend: `useListingEvents` drives `fetchData`/`getPipelineStatus` refetches; a 10 s poll runs only while the SSE socket is not connected. Backend: the SSE route accepts a `token` query parameter (EventSource cannot set headers); `listing_progress` already returns `error`/`attempts` — the frontend types catch up. Add-on purchase calls `runner.enqueue_addon_steps`; a periodic `fail_stuck_listings` implements `PIPELINE_TIMEOUT`. CI: one `test.yml` with a backend job (ruff + pytest + ffmpeg + Postgres) and a frontend job (lint, tsc, vitest, build); `deploy.yml` only triggers Render; `docker.yml` builds on PRs. Docker uses `uv sync --frozen` against a committed `uv.lock`. `just check/test/dev`.

**Tech Stack:** Next.js 16 + React 19 + vitest + eslint 9; FastAPI; GitHub Actions; Docker; uv; just.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` — "Phase 7: frontend, CI, hosting config".

## Global Constraints

- Branch `feat/frontend-ci-hosting` off `feat/video-two-tier` (PR #311). PR targets `feat/video-two-tier`. Never push to `main`; never merge; never amend published commits.
- Frontend gates that CI will enforce and that must pass locally before each frontend commit (run in `frontend/`): `npm run lint` (0 errors; warnings allowed), `npx tsc --noEmit`, `npx vitest run` (0 failed), `NEXT_PUBLIC_MEDIA_HOST=media.example.com NEXT_FONT_GOOGLE_MOCKED_RESPONSES=<path> npm run build` (this sandbox cannot reach Google Fonts; the mocked-responses env var is the documented next/font escape hatch — create a small JSON map file under the scratch dir; CI fetches fonts for real and does not set it).
- **Lint ruling:** fix real defects (`react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps`, `@typescript-eslint/no-unused-vars`, `react/no-unescaped-entities`). Downgrade to `warn` in `eslint.config.*`: `@typescript-eslint/no-explicit-any`, `@next/next/no-img-element`, `react-hooks/set-state-in-effect`, each with a one-line comment naming the follow-up. Cost if wrong: flip three lines back.
- Backend gates: full suite 0 failed (`.venv/Scripts/python.exe -m pytest tests -q --tb=short -p no:cacheprovider`, timeout 600000, never two at once), `ruff check src tests alembic`, `alembic heads` = `056_video_asset_metadata` (no migration this phase).
- Every Bash call passes an explicit timeout; Windows: forward-slash paths; `.env` has `FFMPEG_BIN` and `USE_MOCK_PROVIDERS=true`.
- Commit trailer on every commit:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

---

## File map

| File | Responsibility |
|---|---|
| `frontend/src/app/listings/[id]/page.tsx` | SSE-driven refresh, fallback poll, failed-step error + Retry |
| `frontend/src/components/listings/pipeline-progress.tsx` | accepts `refreshKey`/`connected` props; shows `error`/`attempts`; no own interval while connected |
| `frontend/src/components/listings/pipeline-status.tsx` | stage map uses real `ListingState` values |
| `frontend/src/lib/use-listing-events.ts` | unchanged API; add `.failed` listener and `pipeline.completed` |
| `frontend/src/lib/types.ts`, `frontend/src/lib/generated/api.d.ts` | `PipelineStep.error/attempts`; regenerated OpenAPI types |
| `frontend/src/lib/api-client.ts` | drop `uploadVideo` + `VideoUploadRequest/Response` if unused |
| `frontend/src/__tests__/*` | 6 failing tests fixed; new SSE/poll hook test |
| `frontend/eslint.config.*` | rule downgrades per ruling |
| `src/listingjet/api/sse.py`, `api/deps.py` | `get_current_user_or_query_token` for the SSE route only |
| `src/listingjet/pipeline/runner.py`, `api/addons.py` | `enqueue_addon_steps` |
| `src/listingjet/pipeline/periodic.py`, `config/__init__.py` | `fail_stuck_listings`, `pipeline_timeout_hours` |
| `.github/workflows/test.yml`, `deploy.yml`, `docker.yml`; delete `lint.yml` | CI |
| `Dockerfile`, `uv.lock`, `.gitignore`, `docker-compose.yml`, `render.yaml`, `docker/entrypoint.sh` | hosting |
| `scripts/gen_env_example.py`, `.env.example`; delete `.env.production.example` | env |
| `justfile`, `tests/conftest.py` (`db` auto-marker), `pyproject.toml` (markers) | dev commands |

---

### Task 1: Frontend live updates, failed-step UX, test/lint/build gates

**Files:**
- Modify: `frontend/src/app/listings/[id]/page.tsx:80-90,124-135,390-405`, `frontend/src/components/listings/pipeline-progress.tsx`, `frontend/src/components/listings/pipeline-status.tsx:20-40`, `frontend/src/lib/use-listing-events.ts`, `frontend/src/lib/types.ts:254-265`, `frontend/src/lib/api-client.ts:324-330`, `frontend/eslint.config.*`, `frontend/vitest.config.*` (or `vitest.setup.*`), `frontend/src/__tests__/api-client.test.ts`, `frontend/src/__tests__/ui-components.test.tsx`
- Create: `frontend/src/__tests__/use-listing-events.test.tsx`
- Regenerate: `frontend/src/lib/generated/openapi.json` + `api.d.ts` (`npm run generate-api` after dumping the spec with `.venv/Scripts/python.exe -c "import json; from listingjet.main import app; json.dump(app.openapi(), open('frontend/src/lib/generated/openapi.json','w'), indent=2)"`)

**Interfaces:**
- Consumes: backend `GET /listings/{id}/pipeline-status` → `{listing_id, state, steps: [{name, status: pending|in_progress|completed|failed|skipped, completed_at, progress, error, attempts}]}`; SSE `GET /listings/{id}/events?token=` (Task 2 backend makes the token work; until then the hook already sends it); `POST /listings/{id}/retry`.
- Produces: `PipelineProgress({listingId, listingState, refreshKey: number, live: boolean})` — refetches when `refreshKey` changes; polls every 10 s only when `!live` and the state is a processing state; renders `error` text under a failed step and `attempts` when > 1. `useListingEvents` additionally listens for `pipeline.completed`, `pipeline.failed` and any `*.failed` event names in `_PIPELINE_EVENTS` (mirror `src/listingjet/api/sse.py`).

- [ ] **Step 1: Failing tests**
  - `use-listing-events.test.tsx`: mock `global.EventSource` with a tiny class exposing `onopen/onmessage/addEventListener/close`; render a probe component; assert `connected` flips true on `onopen`, that a dispatched `packaging.completed` named event lands in `events`/`lastEvent`, and that `close()` runs on unmount.
  - `api-client.test.ts`: the four failures are "Invalid URL" because `NEXT_PUBLIC_API_URL` defaults to `/api` under Node. Set `process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000"` in the vitest setup file (add `setupFiles` to `vitest.config` if absent) — do not change production defaults.
  - `ui-components.test.tsx` Badge: the text is rendered inside a `motion.span`; use `screen.getByText("approved", { exact: false })` or query the `span` role — pick whichever matches the component; if the label truly isn't rendered, fix the `Badge` component (that's the bug).
  - Page-level: a test for `PipelineProgress` — render with `live=true` and assert no `setInterval` is scheduled (use `vi.useFakeTimers` + `vi.getTimerCount()`), then `live=false` in a processing state → one interval; a failed step renders its `error` string and a Retry button is present when `listingState === "failed"` (if the Retry button lives on the page, test it there with `apiClient.retryPipeline` mocked).
- [ ] **Step 2: RED**, then implement:
  - `page.tsx`: `const { connected, lastEvent } = useListingEvents(id)`; `useEffect(() => { if (lastEvent) fetchData(); }, [lastEvent, fetchData])`; the existing `setInterval` keeps running only when `!connected` (add `connected` to the effect deps and early-return when connected). Pass `refreshKey={events.length}` and `live={connected}` to `PipelineProgress`. In the FAILED banner (~line 395) show the first failed step's `error` (from the progress data — lift `steps` state up or have `PipelineProgress` call `onSteps`) next to the existing Retry button; Retry already calls `retryPipeline` — keep it, add `disabled={actionLoading}`.
  - `pipeline-progress.tsx`: props per Interfaces; remove `POLL_INTERVAL` polling when `live`; render `step.error` (monospace, truncated to 200 chars with title attr) and `attempt n` badge.
  - `pipeline-status.tsx`: stages → `ingest: ["new","uploading"]`, `analyze: ["analyzing"]`, `review: ["awaiting_review","in_review","approved"]`, `create: ["exporting"]`, `delivered: ["delivered"]`; `ERROR_STATES = failed, pipeline_timeout, cancelled` (unchanged); drop `content`, `brand_social`, `chapters`, `compliance`.
  - `types.ts`: `PipelineStep` gains `error: string | null; attempts?: number`.
  - `api-client.ts`: delete `uploadVideo` and its request/response types if `grep -rn uploadVideo src` shows no caller (report says none); also delete any orphaned `video-upload` component/type.
  - Regenerate `api.d.ts`; `tsc` must stay clean (adjust `types.ts` re-exports if the generated names moved).
  - ESLint: apply the ruling; fix the remaining errors by hand (read each; no `eslint-disable` blanket comments — per-line disables only where the fix is a genuine false positive, with a reason).
- [ ] **Step 3: Gates** — `npm run lint` 0 errors, `npx tsc --noEmit`, `npx vitest run` 0 failed, build with the two env vars (write the fonts mock JSON to the scratch dir: `{"https://fonts.googleapis.com/css2?family=Exo+2:...": "/* mocked */"}` — read `next/font` docs comment in `node_modules/next/dist/compiled/@next/font/dist/google/fetch-css-from-google-fonts.js` for the exact key format, or set the env to a file with `{}` and confirm the build falls back). Record which worked.
- [ ] **Step 4: Commit** — `feat(frontend): SSE-driven listing page, failed-step errors, green lint/test/build gates`.

---

### Task 2: Backend — SSE query token, add-on re-run, stuck-listing watchdog

**Files:**
- Modify: `src/listingjet/api/deps.py` (add `get_current_user_or_query_token`), `src/listingjet/api/sse.py:35-45`, `src/listingjet/pipeline/runner.py` (`enqueue_addon_steps`), `src/listingjet/api/addons.py:33-60,140-160` (call it; widen `allowed_states` to include `APPROVED`, `EXPORTING`, `DELIVERED`), `src/listingjet/pipeline/periodic.py` (`fail_stuck_listings`), `src/listingjet/pipeline/runner.py::periodic_loop` (schedule it hourly), `src/listingjet/config/__init__.py` (`pipeline_timeout_hours: int = 6`), `.env.example` (Task 4 regenerates; fine)
- Tests: `tests/test_api/test_sse.py` (query token accepted; bad token 401; header still works), `tests/test_pipeline/test_addon_rerun.py` (new), `tests/test_pipeline/test_periodic.py` (stuck listing → FAILED with error "pipeline timeout after Nh", listing with a RUNNING job untouched, DELIVERED untouched)

**Interfaces:**
- Produces: `deps.get_current_user_or_query_token(token: str | None = Query(None), ...)` — same validation path as `get_current_user` (access-type check, revocation check) with the query value as the last fallback; used ONLY by the SSE route. `runner.enqueue_addon_steps(session, listing, slug: str, *, steps=PIPELINE) -> int`: for every step whose `gate == f"addon:{slug}"` (`video_ai`, `virtual_staging`) that has no job or a SKIPPED/FAILED/CANCELLED job → insert/reset to QUEUED (`attempts=0`, `run_after=now`); for each step that transitively requires one of those and is DONE/SKIPPED → reset to QUEUED (`social_cuts`, `distribution` and its dependents that exist); return the number of rows touched; if the listing is DELIVERED set `listing.state = EXPORTING` so the UI shows processing, and the last step's completion path (`distribution` → `delivered`) already restores it — verify in `runner.py` how `delivered` is set and reuse. `periodic.fail_stuck_listings(session_factory, *, max_age_hours) -> int`: listings in `UPLOADING/ANALYZING/EXPORTING` whose newest `pipeline_jobs.updated_at` (or `started_at`) is older than `max_age_hours` and that have no RUNNING job → `fail_listing(..., error=f"pipeline timeout after {max_age_hours}h")`, state `PIPELINE_TIMEOUT`.

- [ ] **Step 1: Failing tests** (use existing fixtures in `tests/test_pipeline/conftest.py` and `tests/test_api`); for the add-on test: enqueue a listing with `enabled_addons=[]` → `video_ai` SKIPPED; mark everything through `distribution` DONE (helper `_mark_done`), state DELIVERED; call `enqueue_addon_steps(session, listing, "ai_video_tour")` → `video_ai` QUEUED, `social_cuts` QUEUED, `distribution` QUEUED, `video_baseline` untouched (DONE), returns 3, `listing.state == EXPORTING`; second call is a no-op (0). API test: `POST /listings/{id}/addons` with slug `ai_video_tour` on a DELIVERED listing (credit tenant with enough credits — copy setup from existing addons tests) → 200 and the job rows above.
- [ ] **Step 2: RED → implement → GREEN.** Do not touch `pipeline_jobs` schema. `fail_listing` exists in `runner.py`; reuse it.
- [ ] **Step 3: Full suite, ruff, commit** — `feat(pipeline): add-on re-run after enqueue, stuck-listing watchdog, SSE query-token auth`.

---

### Task 3: CI consolidation

**Files:**
- Modify: `.github/workflows/test.yml` (rename job `backend`; add `Ruff` step before tests; add `frontend` job: `actions/setup-node@v4` node 22 with npm cache on `frontend/package-lock.json`, `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npx vitest run`, `npm run build` with `env: NEXT_PUBLIC_MEDIA_HOST: media.example.com`, `NEXT_PUBLIC_API_URL: /api`), `.github/workflows/deploy.yml` (delete the `test` job and its `needs`; keep checkout-free deploy job: Render deploy hook for the API only — remove the worker trigger; keep Sentry release), `.github/workflows/docker.yml` (`on: pull_request` + `push: main`; `push: false` stays)
- Delete: `.github/workflows/lint.yml` (ruff moves into `test.yml`; drop `pip-audit`/`npm audit` `|| true` steps — Dependabot already reports)

- [ ] **Step 1: Edit; validate YAML** with `.venv/Scripts/python.exe -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"` (install `pyyaml` into the venv if missing — dev-only, don't add to pyproject). `gh workflow list` after push confirms three workflows.
- [ ] **Step 2: Commit** — `ci: one test workflow (backend + frontend jobs), deploy only triggers Render, docker builds on PRs`.

---

### Task 4: Hosting and dev config

**Files:**
- Modify: `Dockerfile` (builder: `pip install uv` → `COPY pyproject.toml uv.lock ./` → `uv sync --frozen --no-dev --no-install-project` then `COPY src/` + `uv sync --frozen --no-dev`; runtime copies `/app/.venv` and sets `PATH=/app/.venv/bin:$PATH`; keep `ffmpeg libpq5 curl`; no Playwright — confirm none present), `.gitignore` (remove `uv.lock`), `docker-compose.yml` (services: `postgres`, `postgres-test`, `redis`, `api` with `WORKER_ENABLED=true`; delete `pgbouncer`, `worker`; keep volumes), `render.yaml` (`plan: free`; add `- key: WORKER_ENABLED value: "true"` and `- key: WORKER_CONCURRENCY value: "2"` if that setting exists; `autoDeploy: false` stays; replace the `.env.production.example` mention in the comment with `.env.example`), `docker/entrypoint.sh` (drop the Railway comment; keep `migrate|api|worker`)
- Create: `uv.lock` (`.venv/Scripts/python.exe -m pip install uv` then `.venv/Scripts/uv.exe lock` from the repo root; commit the lock), `scripts/gen_env_example.py` (iterates `Settings.model_fields`: `KEY=default` for non-secret fields, `KEY=` for fields whose name contains `key|secret|password|token|dsn|url` (mark as `# secret`); groups by a comment header derived from the field's section — use the order in `Settings`; writes `.env.example`; `--check` mode exits 1 if the file would change), `justfile` (`check`: `ruff check src tests alembic` + `pytest -m "not db and not ffmpeg" -q`; `test`: `pytest -q`; `dev`: `uvicorn listingjet.main:app --reload`; `worker`: `python -m listingjet.pipeline.worker`; `env-example`: the script; use `.venv/Scripts/...` paths on Windows via `set windows-shell`? — keep the justfile POSIX and note Windows users run the venv binaries directly)
- Modify: `tests/conftest.py` — `pytest_collection_modifyitems`: add `pytest.mark.db` to any item whose `fixturenames` intersect `{"db_session", "async_client", "client", "engine", "test_engine", "listing", "assets"}` (check the real DB fixture names in `tests/conftest.py`/`tests/test_agents/conftest.py`); `pyproject.toml` markers: add `db: needs Postgres`
- Delete: `.env.production.example`
- Tests: `tests/test_scripts/test_gen_env_example.py` — running the generator produces a line for every `Settings` field and `--check` passes against the committed file; `pytest -m "not db and not ffmpeg" --collect-only -q | tail -1` reports a count > 0 and a run of that subset is green.

- [ ] **Step 1: Implement in the order: conftest marker → justfile → gen script + `.env.example` → uv.lock → Dockerfile/compose/render.** Verify `uv lock` succeeds offline-ish (it needs the index; fine here) and that `uv sync --frozen --no-dev` into a throwaway dir works on this machine (`.venv/Scripts/uv.exe sync --frozen --no-dev --python .venv/Scripts/python.exe --project . --directory <scratch>` or equivalent; if uv can't target another dir, at least `uv lock --check`). Docker itself cannot run here; `docker.yml` on the PR is the build gate — say so in the report.
- [ ] **Step 2: Gates** — full suite, ruff, `just check` equivalent (`pytest -m "not db and not ffmpeg"`), `gen_env_example.py --check`.
- [ ] **Step 3: Commit** — `chore(hosting): uv-locked Docker image, free Render service, trimmed compose, generated .env.example, justfile`.

---

### Task 5: Verification, docs, PR

- [ ] Backend + frontend smoke on this machine: start moto + worker + `uvicorn` (port 8000) as in Phase 6 Task 6; seed a listing; `cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev` (background); with the Playwright MCP tools or the Chrome tools, log in with the seeded credentials, open the listing page, and confirm in the network panel that `/listings/<id>/events` is an open `text/event-stream` request and that no `/pipeline-status` polling repeats while it is connected; approve; confirm the page advances to delivered without a reload. If the browser tooling is unavailable, fall back to `curl -N` on the SSE endpoint with `?token=` and record the events; state which path was used.
- [ ] `CLAUDE.md`: commands section → `just check|test|dev|worker`; CI description; "Migration head: 056" unchanged; providers row unchanged. `MASTER_TODO.md`: Phase 6 row `#311`; Phase 7 row `feat/frontend-ci-hosting` / PR #, "done, awaiting merge"; carried: remove the four Phase 7 lines, the watchdog line, and the post-delivery add-on line; keep ops lines; add "Frontend lint: `no-explicit-any`, `no-img-element`, `set-state-in-effect` downgraded to warnings — N warnings to burn down".
- [ ] Full suite, ruff, frontend gates, `alembic heads` 056. Push; `gh pr create --base feat/video-two-tier --title "feat: live listing page over SSE, CI consolidation, free-tier hosting config (phase 7)"` with body: frontend changes, backend changes (SSE token, add-on re-run, watchdog), CI shape, Docker/uv, render/compose/env, lint ruling + warning count, verification evidence (browser or curl), test summary, merge order `#306 → … → #311 → this`. Attribution lines at the end. Do not merge.

---

## Self-review

- **Spec coverage:** page SSE + fallback poll ✔ T1; pipeline-progress reads job list with status/error ✔ T1; Retry + error text ✔ T1; test.yml backend+frontend jobs, deploy.yml dedupe, docker.yml on PRs, audits removed ✔ T3; render.yaml free/worker/env ✔ T4; compose trimmed ✔ T4; Dockerfile uv.lock ✔ T4; `.env.example` generated ✔ T4; justfile + `db` marker ✔ T4. Carried: `pipeline-status.tsx` stale names ✔ T1; `uploadVideo` dead code ✔ T1; `api.d.ts` regen ✔ T1; build gate ✔ T3; single `vercel.json` ✔ (already only `frontend/vercel.json`); watchdog ✔ T2; post-delivery add-on ✔ T2.
- **Placeholders:** none. **Type consistency:** `PipelineProgress` props (T1 only); `enqueue_addon_steps` name in T2 + `addons.py`; marker name `db` in T4 justfile/pyproject/conftest.
