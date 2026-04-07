# Phase 3: Listing Health Score — Implementation Plan

> **Spec:** `docs/superpowers/specs/2026-04-07-phase3-health-score-design.md`
> **Branch:** `claude/phase3-health-score-dfJn1`
> **Date:** 2026-04-07

---

## Step 1: Database Models + Migration

### New Models

**`src/listingjet/models/listing_health_score.py`**
- `ListingHealthScore` — tenant-scoped, unique on `listing_id`
- Fields: `overall_score`, `media_score`, `content_score`, `velocity_score`, `syndication_score`, `market_score`, `weights` (JSONB), `signals_snapshot` (JSONB), `calculated_at`

**`src/listingjet/models/health_score_history.py`**
- `HealthScoreHistory` — tenant-scoped, append-only
- Fields: `listing_id`, `overall_score`, `media_score`, `content_score`, `velocity_score`, `syndication_score`, `market_score`, `calculated_at`
- Index: `(listing_id, calculated_at)` for efficient trend queries

**`src/listingjet/models/idx_feed_config.py`**
- `IdxFeedConfig` — tenant-scoped
- Fields: `name`, `base_url`, `api_key_encrypted`, `board_id`, `poll_interval_minutes`, `last_polled_at`, `status`

### Migration

**`alembic/versions/037_health_score_and_idx_feed.py`**
- Create `listing_health_scores`, `health_score_history`, `idx_feed_configs` tables
- Add RLS policies for all three tables
- Add indexes: `listing_health_scores(listing_id)` unique, `health_score_history(listing_id, calculated_at)`, `idx_feed_configs(tenant_id)`

### Model Registration

Update `src/listingjet/models/__init__.py` to import all three new models.

---

## Step 2: HealthScoreService

**`src/listingjet/services/health_score.py`**

Core service with sub-score calculators:

```python
class HealthScoreService:
    async def calculate(session, listing_id, tenant_id) -> ListingHealthScore
    async def calculate_media_score(session, listing_id) -> int        # from VisionResult + PackageSelection
    async def calculate_content_score(session, listing_id) -> int      # from Listing state + SocialContent + BrandKit
    async def calculate_velocity_score(session, listing_id) -> int     # from PerformanceEvent timestamps
    async def calculate_syndication_score(session, listing_id) -> int  # from PerformanceEvent idx.* signals
    async def calculate_market_score(session, listing_id) -> int       # from PerformanceEvent idx.* signals
    async def get_weights(session, tenant_id, plan) -> dict            # default or custom weights
    async def get_score(session, listing_id) -> ListingHealthScore     # read cached score
    async def get_trend(session, listing_id, days=90) -> list          # history query
```

Key patterns:
- Each sub-calculator is independent and testable
- Weights are resolved: custom (Enterprise) → plan defaults → global defaults
- Unavailable sub-scores (plan-gated) get weight redistributed
- Results upserted into `listing_health_scores`, appended to `health_score_history`

---

## Step 3: Refactor engagement_score.py

- Move logic from `predict_engagement()` into `HealthScoreService.calculate_media_score()`
- Keep `predict_engagement()` as a thin wrapper that calls the new function
- Update callers in `listings_media.py` and analytics endpoints

---

## Step 4: HealthScoreAgent

**`src/listingjet/agents/health_score.py`**

Extends `BaseAgent`. Called as a Temporal activity after pipeline completion.

```python
class HealthScoreAgent(BaseAgent):
    agent_name = "health_score"
    async def execute(self, context: AgentContext) -> dict:
        # Call HealthScoreService.calculate()
        # Emit health.score.updated event
        # Check alert threshold, emit health.score.alert if needed
```

**`src/listingjet/activities/pipeline.py`** — add `run_health_score` activity.

---

## Step 5: Wire into Temporal Workflow

In `workflows/listing_pipeline.py`, add `run_health_score` activity after `run_distribution` (Phase 2 end). Non-blocking — pipeline completes even if health score calculation fails.

---

## Step 6: API Endpoints

**`src/listingjet/api/health.py`** — new router

- `GET /listings/{id}/health` — score + breakdown + trend
- `GET /listings/health/summary` — tenant-wide stats
- `GET /admin/health/overview` — cross-tenant (admin only)

**`src/listingjet/api/idx_config.py`** — new router

- `POST /settings/idx-feed` — create (Pro+ gated)
- `GET /settings/idx-feed` — list configs
- `PATCH /settings/idx-feed/{id}` — update
- `DELETE /settings/idx-feed/{id}` — remove

**`src/listingjet/api/schemas/health.py`** — Pydantic schemas

Mount both routers in `main.py`.

---

## Step 7: IdxFeedPoller

**`src/listingjet/services/idx_feed_poller.py`**

Background task (same pattern as `OutboxPoller`):

1. Query `idx_feed_configs` where `status = 'active'` and `last_polled_at < now - poll_interval`.
2. For each config, use `RESOAdapter` to fetch property updates.
3. Match RESO properties to listings by address or MLS number.
4. Write `PerformanceEvent` records: `idx.status_change`, `idx.dom_update`, `idx.price_change`, `idx.photo_count`.
5. Trigger health score recalculation for affected listings.
6. Update `last_polled_at`.

Wire into FastAPI lifespan in `main.py` (alongside `OutboxPoller`).

---

## Step 8: Frontend

**Listing card badge:** `frontend/src/components/listings/health-badge.tsx`
- Green/yellow/red dot + score number

**Listing detail panel:** `frontend/src/components/listings/health-panel.tsx`
- Sub-score bars, trend sparkline, actionable callouts
- Plan-gated sections with PlanBadge upgrade prompts

**Health dashboard page:** `frontend/src/app/health/page.tsx`
- Score distribution, top/bottom listings, trend chart, IDX status

**IDX settings:** add to `frontend/src/app/settings/page.tsx`
- IDX feed CRUD form

**API client:** add health + IDX methods to `frontend/src/lib/api-client.ts`

**Types:** add health + IDX types to `frontend/src/lib/types.ts`

**Plan context:** add `health_breakdown`, `health_alerts`, `idx_feed` to feature gating in `plan-context.tsx`

---

## Step 9: Tests

- `tests/test_services/test_health_score.py` — unit tests for each sub-calculator + composite
- `tests/test_agents/test_health_score.py` — agent execution, event emission
- `tests/test_api/test_health.py` — endpoint tests for health + IDX config
- `tests/test_services/test_idx_feed_poller.py` — poller logic

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `models/listing_health_score.py` | Health score model |
| `models/health_score_history.py` | Score history model |
| `models/idx_feed_config.py` | IDX feed config model |
| `services/health_score.py` | Score calculation service |
| `services/idx_feed_poller.py` | IDX feed polling |
| `agents/health_score.py` | Health score agent |
| `api/health.py` | Health API endpoints |
| `api/idx_config.py` | IDX config API endpoints |
| `api/schemas/health.py` | Pydantic schemas |
| `alembic/versions/037_*` | Migration |
| `frontend/.../health-badge.tsx` | Listing card badge |
| `frontend/.../health-panel.tsx` | Detail page panel |
| `frontend/src/app/health/page.tsx` | Health dashboard |
| `tests/test_services/test_health_score.py` | Service tests |
| `tests/test_agents/test_health_score.py` | Agent tests |
| `tests/test_api/test_health.py` | API tests |
| `tests/test_services/test_idx_feed_poller.py` | Poller tests |

### Modified Files
| File | Change |
|------|--------|
| `models/__init__.py` | Import new models |
| `services/engagement_score.py` | Delegate to HealthScoreService |
| `activities/pipeline.py` | Add `run_health_score` activity |
| `workflows/listing_pipeline.py` | Wire health score after distribution |
| `main.py` | Mount health/IDX routers, start IdxFeedPoller |
| `services/plan_limits.py` | Add health feature gating |
| `frontend/src/lib/api-client.ts` | Health + IDX API methods |
| `frontend/src/lib/types.ts` | Health + IDX types |
| `frontend/src/contexts/plan-context.tsx` | Health feature gates |
| `frontend/src/components/listings/listing-card.tsx` | Health badge |
| `frontend/src/app/listings/[id]/page.tsx` | Health panel |
| `frontend/src/app/settings/page.tsx` | IDX config section |
| `frontend/src/components/layout/nav.tsx` | Health nav link |
