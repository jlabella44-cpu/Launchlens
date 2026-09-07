# Phase 3: Delete and Flag — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the features the user agreed to cut, put the deferred ones behind a `FEATURES` flag list, replace the 30k-line vendored Canva SDK with a thin client, drop dead dependencies and repo cruft, and close the Phase 2 residuals.

**Architecture:** One `features` setting (comma list) read through `listingjet.features.enabled(name)`. Backend routers register only when their flag is on; pipeline steps carry a `feature:<name>` gate that `enqueue_pipeline` turns into `skipped`; the frontend fetches `GET /settings/features` once and hides the matching nav items and panels. Deletions are mechanical and verified by grep gates plus the full suite. The Canva provider keeps its public `render()` contract and tests but talks to six REST endpoints through one httpx client.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, httpx, pytest; Next.js 16 + TypeScript, vitest.

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` (section "Phase 3: delete and flag", plus "Phase 2" residuals recorded in PR #307's body).

## Global Constraints

- Branch `chore/delete-and-flag`, created off `feat/job-queue` (PR #307, unmerged, which sits on `fix/security-week1`, PR #306). Never push to `main`; open a PR against `feat/job-queue` at the end; do not merge. Rebase if either parent PR merges first.
- Tooling (Windows): `.venv/Scripts/python.exe -m pytest <paths> -q --tb=short -p no:cacheprovider` from the repo root (full suite ≈ 450 s, use `timeout: 600000`); `.venv/Scripts/ruff.exe check src tests alembic`; `.venv/Scripts/alembic.exe <cmd>`; frontend: `cd frontend && npx tsc --noEmit`, `npm run lint`, `npx vitest run` (`npm run build` does not work on this machine — Turbopack panic — skip it). Postgres dev (5432, at 053) and test (5433) are running; `.env` exists. An interrupted pytest run dirties the test DB: truncate and re-run rather than trusting a partial result.
- Alembic head is `053_pipeline_jobs`; new migration `054_drop_cut_tables` with `down_revision = "053_pipeline_jobs"`.
- Flag names are exactly: `learning`, `health_score`, `performance_intelligence`, `help_agent`, `microsite`, `webhooks`, `listing_permissions`. Default: none enabled.
- Keep (do NOT delete in this phase, later phases replace them): `providers/google_vision.py`, `providers/openai_vision.py`, `providers/kling.py`, `providers/openai_*.py`, `providers/claude.py`, `providers/mock.py`, `agents/video*.py`, `agents/vision.py`, `agents/photo_compliance.py`, `components/listings/pipeline-progress.tsx` (Phase 7 wires it), `docs/superpowers/plans/2026-09-*` and `docs/superpowers/specs/2026-09-*` (this rework's own docs), `docs/reviews/`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

## Findings that shape this plan (verified against the code)

- The vendored Canva SDK (`providers/canva_generated/`, 3.5 MB, 6.4k lines of Python across ~1,000 files) is used for exactly six endpoints: `POST /v1/url-asset-uploads`, `GET /v1/url-asset-uploads/{job_id}`, `POST /v1/autofills`, `GET /v1/autofills/{job_id}`, `POST /v1/exports`, `GET /v1/exports/{export_id}`. Task 6 replaces it.
- `property_verification` runs four Playwright scrapers (`services/property_scraper/`) then cross-references with ATTOM data. Dropping Playwright means the agent verifies from API data only. The agent is optional in the pipeline.
- `tenant_bypass` is a Redis cache in front of `Tenant.bypass_limits`; the column and the admin toggle stay, the cache and the rate-limit checks go.
- `services/metrics.py` (`record_cost`, `record_token_usage`, `StepTimer`) is built on `monitoring.metrics.emit_metric` (CloudWatch). Phase 4 needs `record_cost`/`record_token_usage`, so `emit_metric` becomes a structured log line, not a deletion.
- Frontend components with no importer: `address-lookup.tsx`, `demo-pipeline-status.tsx`, `verification-badge.tsx` (delete); `pipeline-progress.tsx` (keep for Phase 7). `react-hotkeys-hook` has zero imports.
- Phase 2 residuals to close here: shutdown requeue keeps `attempts`; `claim_next`'s 500-row window can still fill with post-approval rows of listings parked at review; `main.py` shutdown no longer catches `CancelledError`; `PhotoComplianceAgent()` is constructed without a session factory in `api/image_edit.py:193` and `api/listings_workflow.py:458`.

## File structure

| File | Responsibility |
|---|---|
| `src/listingjet/features.py` | `FEATURES` set, `enabled(name)`, `require_feature(name)` FastAPI dependency |
| `src/listingjet/api/settings_features.py` | `GET /settings/features` |
| `src/listingjet/providers/canva_client.py` | thin httpx client for the six Canva endpoints |
| `alembic/versions/054_drop_cut_tables.py` | drops `cma_reports`, `idx_feed_configs`, `api_keys` |
| `frontend/src/hooks/use-features.ts` | fetch-once hook + `FeaturesProvider` |
| `MASTER_TODO.md` | rewritten as the phase tracker |

---

### Task 1: Feature flags — backend

**Files:**
- Create: `src/listingjet/features.py`, `src/listingjet/api/settings_features.py`
- Modify: `src/listingjet/config/__init__.py` (add `features: str = ""` next to `cors_origins`), `src/listingjet/main.py` (router registration ~lines 205-241), `src/listingjet/pipeline/definition.py` (gates on `learning`, `health_score`, `performance_intelligence`, `microsite`), `src/listingjet/pipeline/runner.py::_gated_off`, `src/listingjet/services/outbox_poller.py` (~line 68, webhook delivery), `src/listingjet/agents/packaging.py` (~lines 165-185, learning-weight lookup)
- Test: `tests/test_features.py`, `tests/test_pipeline/test_definition.py` (extend), `tests/test_pipeline/test_runner.py` (extend)

**Interfaces:**
- Produces: `listingjet.features.FLAG_NAMES` (frozenset of the seven names), `enabled(name: str) -> bool` (reads `settings.features` each call so tests can patch), `require_feature(name) -> Depends`-style dependency raising `HTTPException(404, "Feature not enabled")`; `Step.gate = "feature:<name>"` understood by `_gated_off`; `GET /settings/features -> {"features": [sorted enabled names]}` (authenticated, any role).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_features.py
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from listingjet import features
from listingjet.pipeline.definition import STEP_INDEX


def test_flag_names_are_exact():
    assert features.FLAG_NAMES == frozenset({
        "learning", "health_score", "performance_intelligence", "help_agent",
        "microsite", "webhooks", "listing_permissions",
    })


def test_enabled_reads_settings_each_call():
    with patch.object(features.settings, "features", ""):
        assert features.enabled("microsite") is False
    with patch.object(features.settings, "features", "microsite, webhooks"):
        assert features.enabled("microsite") is True
        assert features.enabled("webhooks") is True
        assert features.enabled("learning") is False


def test_enabled_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown feature"):
        features.enabled("nope")


@pytest.mark.asyncio
async def test_require_feature_dependency():
    dep = features.require_feature("help_agent")
    with patch.object(features.settings, "features", ""):
        with pytest.raises(HTTPException) as exc:
            await dep()
        assert exc.value.status_code == 404
    with patch.object(features.settings, "features", "help_agent"):
        assert await dep() is None


def test_deferred_steps_carry_feature_gates():
    assert STEP_INDEX["learning"].gate == "feature:learning"
    assert STEP_INDEX["health_score"].gate == "feature:health_score"
    assert STEP_INDEX["performance_intelligence"].gate == "feature:performance_intelligence"
    assert STEP_INDEX["microsite"].gate == "feature:microsite"


@pytest.mark.asyncio
async def test_settings_features_endpoint(async_client):
    import uuid
    email = f"t-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "T", "company_name": "FlagCo", "plan_tier": "free",
    })
    token = reg.json()["access_token"]
    with patch.object(features.settings, "features", "microsite,learning"):
        resp = await async_client.get("/settings/features", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"features": ["learning", "microsite"]}


@pytest.mark.asyncio
async def test_flagged_router_absent_when_off(async_client):
    # help_agent router is registered only when the flag is on at app build time;
    # with the default empty FEATURES the route must not exist.
    resp = await async_client.get("/help/history?session_id=x")
    assert resp.status_code in (401, 404)
    if resp.status_code == 401:
        pytest.skip("router registered at import; see main.py gating")
```

Add to `tests/test_pipeline/test_runner.py`:

```python
@pytest.mark.asyncio
async def test_feature_gate_skips_step_when_flag_off(db_session):
    from unittest.mock import patch
    from listingjet import features
    listing = await _listing(db_session)
    steps = [Step("a"), Step("m", requires=("a",), optional=True, gate="feature:microsite")]
    with patch.object(features.settings, "features", ""):
        await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=steps)
    jobs = await _jobs(db_session, listing.id)
    assert jobs["m"].status == JobStatus.SKIPPED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_pipeline/test_runner.py -q -p no:cacheprovider` (timeout 180000). Expected: ImportError / gate assertion failures.

- [ ] **Step 3: Implement**

`src/listingjet/features.py`:

```python
"""Feature flags. FEATURES is a comma-separated list in the environment.

Deferred features (learning, health score, performance intelligence, help
agent, microsite, webhooks, listing permissions) are off unless listed.
"""
from fastapi import HTTPException

from listingjet.config import settings

FLAG_NAMES = frozenset({
    "learning", "health_score", "performance_intelligence", "help_agent",
    "microsite", "webhooks", "listing_permissions",
})


def enabled_set() -> set[str]:
    raw = settings.features or ""
    names = {n.strip() for n in raw.split(",") if n.strip()}
    unknown = names - FLAG_NAMES
    if unknown:
        raise ValueError(f"unknown feature(s) in FEATURES: {sorted(unknown)}")
    return names


def enabled(name: str) -> bool:
    if name not in FLAG_NAMES:
        raise ValueError(f"unknown feature {name!r}")
    return name in enabled_set()


def require_feature(name: str):
    if name not in FLAG_NAMES:
        raise ValueError(f"unknown feature {name!r}")

    async def _dep() -> None:
        if not enabled(name):
            raise HTTPException(status_code=404, detail="Feature not enabled")

    return _dep
```

`config/__init__.py`, after `cors_origins`:

```python
    # Comma-separated deferred features to enable; see listingjet.features
    features: str = ""
```

`api/settings_features.py`:

```python
from fastapi import APIRouter, Depends

from listingjet import features
from listingjet.api.deps import get_current_user

router = APIRouter()


@router.get("/features")
async def list_features(_user=Depends(get_current_user)) -> dict:
    return {"features": sorted(features.enabled_set())}
```

Register in `main.py` next to `tenant_settings`: `app.include_router(settings_features.router, prefix="/settings", tags=["settings"])`.

Router gating in `main.py`: wrap the six flagged routers:

```python
    from listingjet import features as _features
    if _features.enabled("listing_permissions"):
        app.include_router(listing_permissions.router, prefix="/listings", tags=["listing-permissions"])
    if _features.enabled("microsite"):
        app.include_router(microsite.router, prefix="/listings", tags=["listings"])
    if _features.enabled("help_agent"):
        app.include_router(help_agent.router, prefix="/help", tags=["help-agent"])
    if _features.enabled("health_score"):
        app.include_router(listing_health.router, tags=["listing-health"])
    if _features.enabled("performance_intelligence"):
        app.include_router(performance.router, tags=["performance"])
        app.include_router(performance_intelligence.router, tags=["performance-intelligence"])
```

(`team.py` imports `deps_permissions` for invites — leave `team.router` registered unconditionally.) Because routers are chosen at app-build time, tests that exercise a flagged router must set `FEATURES` in the environment before `listingjet.main` is imported: add `os.environ.setdefault("FEATURES", "learning,health_score,performance_intelligence,help_agent,microsite,webhooks,listing_permissions")` at the top of `tests/conftest.py` (next to the `WORKER_ENABLED` line) so the existing route tests keep passing, and make the two `test_features.py` tests that assert "off" behaviour patch `features.settings.features` rather than rely on build-time absence (the `test_flagged_router_absent_when_off` test above should instead assert that `require_feature` is attached: change it to call `GET /help/history?session_id=x` with a valid token and `patch.object(features.settings, "features", "")` and expect 404 — and add `dependencies=[Depends(require_feature("help_agent"))]` to the `help_agent`, `microsite`, `listing_health`, `performance`, `performance_intelligence`, `listing_permissions` routers' `APIRouter(...)` constructors so runtime checks hold even when the router was registered).

`definition.py`: `Step("microsite", ..., gate="feature:microsite")`, `Step("learning", ..., gate="feature:learning")`, `Step("health_score", ..., gate="feature:health_score")`, `Step("performance_intelligence", ..., gate="feature:performance_intelligence")`.

`runner._gated_off`, before the `raise`:

```python
    if step.gate.startswith("feature:"):
        from listingjet import features
        return not features.enabled(step.gate.removeprefix("feature:"))
```

`services/outbox_poller.py` around line 68: `if webhook_url and features.enabled("webhooks"):` (import at top). `agents/packaging.py`: wrap the `LearningWeight`/`PhotoOutcomeCorrelation` queries in `if features.enabled("learning"):` and otherwise use `weight_map = {}` and `outcome_boost_map = {}`.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_pipeline tests/test_api/test_listing_health.py tests/test_api/test_settings.py tests/test_services/test_outbox_poller.py tests/test_agents/test_packaging.py -q -p no:cacheprovider` (timeout 300000; adjust the list to files that exist). Expected: PASS. Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/listingjet/features.py src/listingjet/api/settings_features.py src/listingjet/config/__init__.py src/listingjet/main.py src/listingjet/pipeline src/listingjet/services/outbox_poller.py src/listingjet/agents/packaging.py src/listingjet/api/help_agent.py src/listingjet/api/microsite.py src/listingjet/api/listing_health.py src/listingjet/api/performance.py src/listingjet/api/performance_intelligence.py src/listingjet/api/listing_permissions.py tests
git commit -m "feat(flags): FEATURES setting gates deferred routers, pipeline steps, webhooks, learning"
```

---

### Task 2: Feature flags — frontend, and frontend dead code

**Files:**
- Create: `frontend/src/hooks/use-features.ts`
- Modify: `frontend/src/app/auth-wrapper.tsx` (wrap with provider; hide `HelpChat` unless `help_agent`), `frontend/src/components/layout/nav.tsx` (hide Performance and Health links unless their flags), `frontend/src/app/listings/[id]/page.tsx` (hide `HealthPanel` unless `health_score`, `SharePanel` unless `listing_permissions`, remove `VideoUpload`), `frontend/src/app/analytics/page.tsx` (hide `PerformanceIntelligence` unless `performance_intelligence`), `frontend/src/app/settings/page.tsx` (hide health-weights and IDX sections; IDX is deleted outright in Task 3 — remove that section here), `frontend/src/lib/api-client.ts` (add `getFeatures()`), `frontend/package.json` (drop `react-hotkeys-hook`)
- Delete: `frontend/src/components/listings/address-lookup.tsx`, `demo-pipeline-status.tsx`, `verification-badge.tsx`, `video-upload.tsx`
- Test: `frontend/src/hooks/use-features.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/hooks/use-features.test.ts
import { describe, expect, it } from "vitest";
import { parseFeatures } from "./use-features";

describe("parseFeatures", () => {
  it("returns a set of enabled names", () => {
    expect(parseFeatures({ features: ["microsite", "webhooks"] }).has("microsite")).toBe(true);
    expect(parseFeatures({ features: ["microsite"] }).has("learning")).toBe(false);
  });
  it("tolerates a missing body", () => {
    expect(parseFeatures(undefined).size).toBe(0);
  });
});
```

Look at an existing vitest file under `frontend/src/__tests__/` or `frontend/src/app/analytics/performance/page.test.tsx` for the import style and config, and match it.

- [ ] **Step 2: Run to verify it fails**

Run in `frontend/`: `npx vitest run src/hooks/use-features.test.ts` (timeout 300000). Expected: cannot resolve `./use-features`.

- [ ] **Step 3: Implement**

```ts
// frontend/src/hooks/use-features.ts
"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient } from "@/lib/api-client";

export type FeatureName =
  | "learning" | "health_score" | "performance_intelligence" | "help_agent"
  | "microsite" | "webhooks" | "listing_permissions";

export function parseFeatures(body: { features?: string[] } | undefined): Set<FeatureName> {
  return new Set((body?.features ?? []) as FeatureName[]);
}

const FeaturesContext = createContext<Set<FeatureName>>(new Set());

export function FeaturesProvider({ children, enabled }: { children: ReactNode; enabled?: boolean }) {
  const [features, setFeatures] = useState<Set<FeatureName>>(new Set());
  useEffect(() => {
    if (enabled === false) return;
    let cancelled = false;
    apiClient.getFeatures().then((body) => { if (!cancelled) setFeatures(parseFeatures(body)); }).catch(() => {});
    return () => { cancelled = true; };
  }, [enabled]);
  return <FeaturesContext.Provider value={features}>{children}</FeaturesContext.Provider>;
}

export function useFeature(name: FeatureName): boolean {
  return useContext(FeaturesContext).has(name);
}
```

(Rename the file to `use-features.tsx` since it contains JSX; keep the test import path.) `api-client.ts`: `getFeatures() { return this.request<{ features: string[] }>("/settings/features"); }` following the neighbouring methods' style. Mount `FeaturesProvider` inside `auth-wrapper.tsx` around the authenticated tree with `enabled={!!user}` (read how `user` is obtained there). Then gate: `nav.tsx` lines 59-60 and 97 (`useFeature("performance_intelligence")`, `useFeature("health_score")`); listing page `HealthPanel`/`SharePanel`; analytics page `PerformanceIntelligence`; `auth-wrapper.tsx` `HelpChat` behind `useFeature("help_agent")`; settings page health-weights section behind `useFeature("health_score")` and delete its IDX section plus the four `idx-feed` methods in `api-client.ts`.

Delete the four components; remove the `VideoUpload` import/usage from the listing page; `npm uninstall react-hotkeys-hook` (updates `package-lock.json`).

- [ ] **Step 4: Verify**

Run in `frontend/`: `npx tsc --noEmit` (timeout 300000), `npm run lint` (pre-existing errors are acceptable; no new ones), `npx vitest run` (timeout 300000). Expected: typecheck clean, new test passes.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): feature flags hide deferred UI; drop dead components and react-hotkeys-hook"
```

---

### Task 3: Delete CMA, market tracker, IDX/RESO, comparables, drip, API keys, tenant-bypass cache, launch, admin providers, feature tags, engagement score

**Files:**
- Delete: `src/listingjet/agents/cma_report.py`, `src/listingjet/api/cma.py`, `src/listingjet/api/launch.py`, `src/listingjet/api/admin_providers.py`, `src/listingjet/models/cma_report.py`, `src/listingjet/models/idx_feed_config.py`, `src/listingjet/models/api_key.py`, `src/listingjet/services/market_tracker.py`, `idx_feed_poller.py`, `reso_adapter.py`, `comparables.py`, `drip_scheduler.py`, `tenant_bypass.py`, `feature_tags.py`, `engagement_score.py`, `api_keys.py`, `src/listingjet/providers/repliers.py`; tests: `tests/test_agents/test_cma_report.py`, `tests/test_api/test_cma_gate.py`, `tests/test_api/test_activity_usage_apikeys.py`, `tests/test_services/test_api_keys.py`, `test_comparables.py`, `test_drip_scheduler.py`, `test_engagement_score.py`, `test_feature_tags.py`, `test_reso_adapter.py`, `tests/test_providers/test_repliers.py`
- Modify: `src/listingjet/main.py` (imports, lifespan pollers, router lines), `src/listingjet/models/__init__.py`, `src/listingjet/api/credits.py:42` (drop the `cma_report` label), `src/listingjet/api/listings_core.py:18,321` (drop `CMAReport` cascade), `src/listingjet/api/listing_health.py` (drop the four `/settings/idx-feed` endpoints and the `IdxFeedConfig` import), `src/listingjet/api/tenant_settings.py:195-225` (drop API-key endpoints + request model), `src/listingjet/services/account_lifecycle.py` (drop `APIKey` deletion), `src/listingjet/api/admin_tenants.py` (drop `set_tenant_bypass` import and calls; keep the `/bypass-limits` column toggle), `src/listingjet/middleware/rate_limit.py:90-94` and `src/listingjet/services/endpoint_rate_limit.py:58-62` (drop the bypass check), `src/listingjet/api/auth.py:90-92` (drop the drip comment), `src/listingjet/api/listings_workflow.py` pipeline-status (drop the engagement/features block; return `"engagement_score": None, "detected_features": []`), `src/listingjet/config/__init__.py` (drop `reso_*`, `repliers_*`, `attom`? — keep `attom_api_key`, `walk_score_api_key`, `property_lookup_cache_ttl`, `property_verification_enabled`; drop `scraper_rate_limit_seconds` in Task 4), `tests/test_api/test_admin_tenant_controls.py` (drop the two Redis-cache bypass tests; keep the toggle and quota tests), `tests/conftest.py` (drop the `tenant_bypass._get_redis` patch)
- Create: `alembic/versions/054_drop_cut_tables.py`

- [ ] **Step 1: Migration**

```python
"""drop cut-feature tables: cma_reports, idx_feed_configs, api_keys

Revision ID: 054_drop_cut_tables
Revises: 053_pipeline_jobs
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "054_drop_cut_tables"
down_revision = "053_pipeline_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("cma_reports", "idx_feed_configs", "api_keys"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    # Irreversible by design: the features were removed. Recreate from the
    # original migrations (cma: grep 'cma_reports' in alembic/versions; idx: 041; api_keys: grep) if ever needed.
    raise RuntimeError("054_drop_cut_tables cannot be downgraded")
```

Find the exact table names with `grep -rn "__tablename__" src/listingjet/models/cma_report.py src/listingjet/models/idx_feed_config.py src/listingjet/models/api_key.py` BEFORE deleting the models and adjust. Any enum types those tables own (`grep -n "ENUM\|Enum" alembic/versions/*cma* alembic/versions/041*`) get `DROP TYPE IF EXISTS` too.

- [ ] **Step 2: Delete and rewire**

`git rm` the files listed. Then `grep -rn "cma\|CMA\|idx_feed\|IdxFeed\|market_tracker\|MarketTracker\|reso_\|comparables\|repliers\|drip\|tenant_bypass\|feature_tags\|engagement_score\|api_keys\|APIKey\|api_key\b\|admin_providers\|launch\b" src tests --include=*.py | grep -v __pycache__` and fix every hit per the Modify list (note `api_key` also matches `anthropic_api_key` etc. in config — only remove the `APIKey` model usages). In `main.py` lifespan remove the IDX and market tracker blocks and their imports. Frontend: `grep -rn "cma\|CMA\|api-keys\|apiKey\|/admin/providers\|launch" frontend/src --include=*.ts --include=*.tsx` and remove the API-client methods and any UI (`settings` API-key section, admin providers tab) that call deleted endpoints; run `npx tsc --noEmit` after.

- [ ] **Step 3: Verify**

Run: `.venv/Scripts/alembic.exe heads` → `054_drop_cut_tables`; `.venv/Scripts/alembic.exe upgrade head` on the dev DB (timeout 120000). `.venv/Scripts/python.exe -c "import listingjet.main"`. Full suite (timeout 600000): 0 failed. Ruff clean. `npx tsc --noEmit` clean.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete CMA, market tracker, IDX/RESO, comparables, drip, API keys, bypass cache, launch, provider routing admin"
```

---

### Task 4: Delete chapter agent, dead providers, provider routing, Playwright scrapers; simplify the factory

**Files:**
- Delete: `src/listingjet/agents/chapter.py`, `tests/test_agents/test_chapter.py`, `src/listingjet/providers/qwen.py`, `gemma.py`, `elevenlabs.py`, `fallback.py`, `_routing.py`, `src/listingjet/providers/templates/`, `src/listingjet/services/property_scraper/` (all), `tests/test_providers/test_qwen_gemma.py`, `test_qwen_vision.py`, `test_fallback.py`, `test_routing.py`, `tests/test_services/test_scrapers/`, `tests/test_services/test_cross_reference.py`
- Modify: `src/listingjet/pipeline/definition.py` (remove the `chapters` step; `social_cuts` requires `("video", "await_review")`; `distribution` requires drop `"chapters"`), `src/listingjet/pipeline/steps.py` (remove `chapters`), `src/listingjet/api/sse.py:30` (drop `"chapters.completed"`), `src/listingjet/providers/factory.py` (no routing: `get_llm_provider()` → `ClaudeProvider`, `get_vision_provider()` → `GoogleVisionProvider`, `get_tier2_vision_provider()` → `OpenAIVisionProvider`, mocks when `use_mock_providers`; keep the `agent=`/`tenant_id=` kwargs accepted-and-ignored so callers need no change), `src/listingjet/config/__init__.py` (drop `qwen_api_key`, `gemini_api_key`, `agent_model_routing`, `tenant_model_routing`, `llm_fallback_enabled`, `gemma_*`, `qwen_enable_cache`, `vision_provider_tier1/2`, `elevenlabs_*`, `scraper_rate_limit_seconds`; fix `validate_provider_keys` if it references them), `src/listingjet/agents/property_verification.py` (API-only verification, see below), `src/listingjet/services/metrics.py` rate card entries for qwen/gemma if present, `Dockerfile` (delete the `pip install playwright && playwright install chromium --with-deps` line), `pyproject.toml` (drop `playwright`), `tests/test_agents/test_property_verification.py`, `tests/test_providers/test_factory.py`, `test_factory_real.py`, `tests/test_pipeline/test_definition.py` (24 → 23 steps), `tests/test_pipeline/test_steps.py`

Property verification without scrapers — replace steps 6-8 in `agents/property_verification.py`:

```python
                # Verification from API data only (site scrapers were removed in Phase 3).
                property_data.verification_status = "api_only" if api_data else "unverified"
                property_data.field_confidence = {k: 1.0 for k in api_data}
                property_data.mismatches = []
                property_data.scraped_data = {}
                property_data.sources_checked = ["attom"] if api_data else []
                property_data.verified_at = datetime.now(timezone.utc)
                xref = {"status": property_data.verification_status,
                        "field_confidence": property_data.field_confidence,
                        "mismatches": [], "sources_checked": property_data.sources_checked}
```

Check `models/property_data.py` for the allowed `verification_status` values (enum or free string) and use an existing value if it is constrained.

- [ ] **Step 1: Tests first** — update `tests/test_pipeline/test_definition.py` to assert `"chapters" not in STEP_INDEX` and `STEP_INDEX["social_cuts"].requires == ("video", "await_review")`; update `test_property_verification.py` to the API-only expectations; run to see them fail.
- [ ] **Step 2: Delete and rewire**, then grep gate: `grep -rn "chapter\b\|ChapterAgent\|qwen\|gemma\|elevenlabs\|FallbackLLMProvider\|_routing\|resolve_llm_provider\|resolve_vision_provider\|property_scraper\|playwright\|run_all_scrapers\|cross_reference" src tests Dockerfile pyproject.toml --include=* | grep -v __pycache__` must be empty (the `chapters` JSON column on `VideoAsset` and `video.chapters` in `listings_video.py` stay — they are data, Phase 6 fills them).
- [ ] **Step 3: Verify** — `pip install -e ".[dev]" -q` then `pip uninstall -y playwright` (timeout 600000); `import listingjet.main`; full suite 0 failed; ruff clean.
- [ ] **Step 4: Commit** — `git add -A && git commit -m "chore: remove chapter agent, dead LLM/vision providers, provider routing, Playwright scrapers"`

---

### Task 5: Observability — drop OpenTelemetry and CloudWatch, keep Sentry, drop dead deps

**Files:**
- Delete: `src/listingjet/telemetry.py`, `src/listingjet/monitoring/middleware.py`, `src/listingjet/monitoring/metrics.py`, `tests/test_monitoring/test_telemetry.py`, `tests/test_monitoring/test_middleware.py`, `tests/test_monitoring/test_metrics.py` (rewrite the parts that test `services/metrics.py` into `tests/test_services/test_metrics_logging.py`)
- Modify: `src/listingjet/monitoring/__init__.py` (Sentry only), `src/listingjet/agents/base.py` (drop `agent_span`; `instrumented_execute` keeps `StepTimer` and consent check), `src/listingjet/services/metrics.py` (`emit_metric` becomes a local function that logs `logger.info("metric name=%s value=%s unit=%s %s", ...)` — keep `record_cost`, `record_token_usage`, `record_provider_call`, `StepTimer`, `record_review_turnaround` signatures), `src/listingjet/pipeline/worker.py` (call `init_sentry(dsn=settings.sentry_dsn, environment=settings.app_env, release=settings.git_sha)` before the loops), `src/listingjet/config/__init__.py` (drop `otel_exporter_endpoint`, `cloudwatch_enabled`), `pyproject.toml` (drop the six `opentelemetry-*`, `imagehash`, `passlib[bcrypt]` — first confirm `grep -rn "passlib\|imagehash" src` is empty; if `passlib` is used, keep it), `render.yaml` / `.env.example` / `.env.production.example` / `docker-compose.yml` (drop `CLOUDWATCH_ENABLED`, `OTEL_*`, jaeger service)
- Test: `tests/test_services/test_metrics_logging.py`:

```python
import logging

from listingjet.services import metrics


def test_record_cost_logs_a_metric_line(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        metrics.record_cost("vision", "google_vision", 3)
    assert any("metric" in r.message and "vision" in r.message for r in caplog.records)


def test_step_timer_logs_duration(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        with metrics.StepTimer("packaging"):
            pass
    assert any("packaging" in r.message for r in caplog.records)
```

- [ ] Steps: tests first (RED), implement, grep gate `grep -rn "opentelemetry\|otel\|cloudwatch\|CloudWatch\|agent_span\|init_tracing\|emit_metric\|imagehash\|passlib" src tests pyproject.toml render.yaml docker-compose.yml .env.example .env.production.example --include=* | grep -v __pycache__` shows only `services/metrics.py`'s own `emit_metric`; reinstall deps and `pip uninstall -y` the removed packages; full suite 0 failed; ruff clean; commit `chore(observability): drop OpenTelemetry and CloudWatch, keep Sentry (worker included)`.

---

### Task 6: Replace the vendored Canva SDK with a thin client

**Files:**
- Create: `src/listingjet/providers/canva_client.py`
- Modify: `src/listingjet/providers/canva.py` (use the client; keep `CanvaTemplateProvider.__init__(api_key, llm_provider=None, access_token=None)`, `render(template_id, data) -> bytes`, `_build_autofill_data` returning a plain dict, and the module-level poll helpers' behaviour), `tests/test_providers/test_canva.py` (mock `CanvaClient` methods instead of generated functions)
- Delete: `src/listingjet/providers/canva_generated/`, `openapitools.json`, `scripts/generate-canva-client.sh`, `docs/canva-template-setup.md` only if it documents the generator (read it first; keep template setup docs)
- Test: `tests/test_providers/test_canva_client.py` (pytest-httpx)

**Interfaces:**
```python
class CanvaClient:
    def __init__(self, token: str, base_url: str = "https://api.canva.com/rest", timeout: float = 60.0): ...
    async def __aenter__(self) -> "CanvaClient"; async def __aexit__(...)
    async def create_url_asset_upload(self, name: str, url: str) -> str          # job id
    async def get_url_asset_upload(self, job_id: str) -> dict                    # {"status": "in_progress|success|failed", "asset_id": str|None}
    async def create_autofill(self, brand_template_id: str, data: dict) -> str   # job id
    async def get_autofill(self, job_id: str) -> dict                             # {"status": ..., "design_id": str|None}
    async def create_export(self, design_id: str, fmt: dict) -> str               # job id; fmt e.g. {"type": "pdf"}
    async def get_export(self, job_id: str) -> dict                               # {"status": ..., "urls": list[str]}
    async def download(self, url: str) -> bytes
```
Each `create_*` posts JSON to the path in "Findings" with `Authorization: Bearer <token>`, raises `CanvaError(status_code, body)` on non-2xx or when the body has an `"error"` key, and returns `body["job"]["id"]`. Each `get_*` GETs `<path>/{id}` and normalises: status from `job["status"]`, `asset_id` from `job["asset"]["id"]`, `design_id` from `job["result"]["design"]["id"]`, `urls` from `job["urls"]`, absent keys → `None`/`[]`.

- [ ] **Step 1: Client tests (pytest-httpx)**

```python
# tests/test_providers/test_canva_client.py
import pytest

from listingjet.providers.canva_client import CanvaClient, CanvaError


@pytest.mark.asyncio
async def test_create_autofill_posts_and_returns_job_id(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/autofills",
                            json={"job": {"id": "af_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.create_autofill("tpl", {"x": {"type": "text", "text": "y"}}) == "af_1"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer tok"
    assert req.read() == b'{"brand_template_id": "tpl", "data": {"x": {"type": "text", "text": "y"}}}'


@pytest.mark.asyncio
async def test_get_autofill_normalises_result(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/autofills/af_1",
                            json={"job": {"id": "af_1", "status": "success", "result": {"type": "create_design", "design": {"id": "d_9"}}}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_autofill("af_1") == {"status": "success", "design_id": "d_9"}


@pytest.mark.asyncio
async def test_error_body_raises(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/exports", status_code=400,
                            json={"error": {"code": "bad", "message": "nope"}})
    async with CanvaClient(token="tok") as c:
        with pytest.raises(CanvaError) as exc:
            await c.create_export("d_9", {"type": "pdf"})
    assert exc.value.status_code == 400
```

Confirm `pytest-httpx` is installed (`pyproject.toml` dev deps list it) and its fixture name is `httpx_mock`. The JSON byte comparison depends on key order; if `json.dumps` ordering differs, compare `json.loads(req.read())` instead.

- [ ] **Step 2: Implement `canva_client.py`** (httpx `AsyncClient` with `base_url`, `headers={"Authorization": f"Bearer {token}"}`, `timeout`), then rewrite `canva.py` to use it: `async with CanvaClient(token=self._effective_token) as client:` → upload (optional) → `create_autofill(template_id, _build_autofill_data(data, hero_asset_id))` → poll `get_autofill` (20 × 2 s) → `create_export(design_id, {"type": "pdf"})` → poll `get_export` (20 × 2 s) → `client.download(urls[0])`. Keep the hero-upload `try/except` that logs and continues.
- [ ] **Step 3: Port `tests/test_providers/test_canva.py`** — the five existing tests keep their names and intent; replace the generated-function patches with `patch("listingjet.providers.canva.CanvaClient")` returning an `AsyncMock` whose methods return the same shapes; assert the same call order and that `render()` returns the PDF bytes.
- [ ] **Step 4: Delete `canva_generated/`, the generator files**; grep gate `grep -rn "canva_generated\|openapi-generator\|asyncio_detailed" src tests scripts docs pyproject.toml openapitools.json 2>/dev/null` must be empty; `.gitignore` entry for the generated dir removed if present.
- [ ] **Step 5: Verify** — `tests/test_providers tests/test_agents/test_brand.py` green, full suite 0 failed, ruff clean; commit `refactor(canva): thin httpx client replaces the 30k-line generated SDK`.

---

### Task 7: Repo cruft and docs

**Files:**
- Delete: `structure.txt`, `railway.json`, `.vercel/`, `infra/`, root `vercel.json`, `CLOUD_MIGRATION_GUIDE.md`, `TODO.md`, `TODO-video-template.md`, `docs/PRE_LAUNCH_INFRA_CHECKLIST.md`, `docs/runbooks/cdk-deploy-recovery.md`, `docs/plans/`, `docs/archive/`, `docs/SESSION-HANDOFF.md`, `docs/SESSION-HANDOFF-PHASE3.md`, `docs/VIDEO-PIPELINE-HANDOFF.md`, `docs/LISTING-PERMISSIONS-PLAN.md`, `docs/superpowers/plans/2026-03-*` and `2026-04-*`, `docs/superpowers/specs/2026-03-*` and `2026-04-*`, `scripts/run_prod_migrations.sh` and `scripts/prod_smoke.sh` if they reference ECS/AWS (read first)
- Modify: `README.md` (remove infra/CDK/AWS/Railway/Temporal mentions; point at `render.yaml` and the pipeline package), `CLAUDE.md` (remove the "Infra & ops" CDK/Railway/vercel rows, the "What's been done" list, the AWS migration section; add "Feature flags: `FEATURES=`" and "Migration head: 054"; Phase 8 does the full rewrite), `.gitignore` (drop `structure.txt`/`.vercel` lines if present), `MASTER_TODO.md` (replace wholesale with the content below), `.github/workflows/*.yml` (remove any `infra/` or CDK steps; leave the rest for Phase 7)

`MASTER_TODO.md` replacement:

```markdown
# ListingJet — Master TODO

Rework tracker. Spec: `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md`.

| Phase | Branch / PR | Status |
|---|---|---|
| 1 Security fixes | `fix/security-week1` / #306 | done, awaiting merge |
| 2 Job queue replaces Temporal | `feat/job-queue` / #307 | done, awaiting merge |
| 3 Delete and flag | `chore/delete-and-flag` | done, awaiting merge |
| 4 Claude providers + photo analysis | — | next |
| 5 Content + social | — | |
| 6 Video two-tier (ffmpeg + Runway) | — | |
| 7 Frontend, CI, hosting config | — | |
| 8 Docs rewrite | — | |

## Carried items
- Phase 4: Claude provider passes `temperature` (rejected by current SDK); vision tier 1 swallows provider errors; record real token usage.
- Phase 6: `VideoAsset.chapters` derived from the clip manifest (chapter agent removed in Phase 3).
- Phase 7: frontend build gate in CI (cannot build on the dev machine); wire `pipeline-progress.tsx` to SSE; single `vercel.json` in `frontend/`.
- Pipeline watchdog to replace Temporal's execution timeout (`PIPELINE_TIMEOUT` state is unused).
- Operational: create Supabase/Upstash/R2/Render/Vercel/Runway accounts (spec "Operational steps").
```

- [ ] Steps: delete, edit, `git status` sanity, grep `grep -rn "infra/\|cdk\|railway\|CLOUD_MIGRATION\|structure.txt\|PRE_LAUNCH_INFRA\|TODO.md" README.md CLAUDE.md .github docs/runbooks scripts --include=* -i` must be empty, full suite unaffected (run `tests/test_config` only), commit `chore(repo): remove AWS/CDK/Railway remnants, stale plans and handoffs; new MASTER_TODO`.

---

### Task 8: Phase 2 residuals in the runner and API

**Files:**
- Modify: `src/listingjet/pipeline/runner.py` (`requeue_owned` and `_requeue` decrement `attempts` by 1 with a floor of 0; `claim_next` excludes post-approval rows of listings whose `await_review` job is `waiting`), `src/listingjet/main.py` (shutdown: `except (asyncio.TimeoutError, asyncio.CancelledError)` around the worker awaits so the Redis close still runs), `src/listingjet/api/image_edit.py:193` and `src/listingjet/api/listings_workflow.py:458` (`PhotoComplianceAgent(session_factory=admin_session)`)
- Test: `tests/test_pipeline/test_runner_scale.py` (extend), `tests/test_pipeline/test_worker.py` (extend)

`claim_next` exclusion — compute once at import: `POST_REVIEW_STEPS = frozenset(name for name in topological_order(PIPELINE) if "await_review" in transitive_requires(name))` (write `transitive_requires(name) -> set[str]` in `definition.py` with a test), then in the candidate query add:

```python
        .where(~(
            PipelineJob.step.in_(POST_REVIEW_STEPS)
            & exists().where(
                PipelineJob.listing_id == candidate.listing_id  # use an aliased PipelineJob for the subquery
                , alias.step == "await_review", alias.status == JobStatus.WAITING)
        ))
```

Use `sqlalchemy.orm.aliased(PipelineJob)` for the correlated subquery. When `steps` is not the default `PIPELINE` (tests), derive the post-review set from the passed `steps` the same way.

Tests: (a) 45 listings parked at review + one fresh listing → the fresh listing's `ingestion` is claimable on the first call (this is the deadlock regression at scale; use stub functions and the real `PIPELINE`); (b) `requeue_owned` after a claim leaves `attempts == 0`; (c) `transitive_requires("distribution")` contains `await_review` and `transitive_requires("packaging")` does not.

- [ ] Steps: tests RED → implement → `tests/test_pipeline` green → full suite 0 failed → ruff → commit `fix(pipeline): shutdown requeue refunds the attempt; claim scan skips post-review rows of parked listings; admin session for compliance handlers`.

---

### Task 9: Verification and PR

- [ ] `alembic heads` = `054_drop_cut_tables`; `upgrade head` on the dev DB.
- [ ] Full suite 0 failed; ruff clean; `frontend`: `npx tsc --noEmit`, `npm run lint` (no new errors), `npx vitest run`.
- [ ] Line-count check for the PR body: `git diff --shortstat feat/job-queue..HEAD`.
- [ ] `git push -u origin chore/delete-and-flag`; `gh pr create --base feat/job-queue --title "chore: delete cut features, flag deferred ones, drop the Canva SDK and dead deps (phase 3)" --body-file <body>` with: what was deleted (with the diff shortstat), the seven flags and what each gates, the Canva client, property verification now API-only, observability now Sentry + logs, the Phase 2 residuals closed, migration 054 is irreversible by design. End with the two attribution lines. Do not merge.
