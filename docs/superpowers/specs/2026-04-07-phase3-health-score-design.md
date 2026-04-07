# Phase 3: Listing Health Score — Design Spec

> **Version:** 1.0 | **Date:** 2026-04-07 | **Status:** Active
> **Depends on:** Phase 1 (media pipeline), Phase 2 (social features)

---

## 1. Overview

The Listing Health Score is a **composite 0–100 score** that answers "how complete, well-optimized, and market-ready is this listing?" It is computed entirely from automated data sources — pipeline events, vision results, content output, RESO/IDX feed status, and performance events. **No manual entry.**

It replaces the existing single-dimension `predict_engagement()` heuristic in `engagement_score.py` with a multi-dimensional system that evolves as more signals become available.

---

## 2. Goals

1. Give photographers and agents an at-a-glance quality signal for every listing.
2. Surface actionable insights ("your photo quality is dragging down your score").
3. Connect listing preparation quality to market outcomes via IDX/RESO data.
4. Create an Enterprise upsell path (benchmarking, custom weights, multi-board IDX).
5. Power health-drop alerting through the existing webhook/outbox infrastructure.

### Non-Goals

- Portal scraping (Zillow, Realtor.com) — deferred to Phase 4.
- Manual quality assessments or user-entered data.
- Replacing the human review step in the pipeline.

---

## 3. Score Architecture

```
Listing Health Score (0–100)
├── Media Quality      (30%)  ← evolves existing engagement_score.py
│   ├── avg photo quality_score (from VisionResult)
│   ├── avg commercial_score (from VisionResult)
│   ├── hero photo strength (hero_candidate commercial_score)
│   └── coverage completeness (% of required shots present)
│
├── Content Readiness  (20%)  ← pipeline completion signals
│   ├── description generated (dual-tone)
│   ├── FHA compliance passed (no violations)
│   ├── social content generated (if plan allows)
│   ├── brand flyer generated
│   └── MLS + marketing bundles exported
│
├── Pipeline Velocity  (15%)  ← timing signals from PerformanceEvent
│   ├── upload → delivered elapsed time (vs. tenant median)
│   ├── review turnaround time (vs. tenant median)
│   ├── override rate (lower = AI selections trusted = healthier)
│   └── no failures/retries in pipeline
│
├── Syndication Status (20%)  ← RESO adapter polling
│   ├── listing active in IDX feed
│   ├── photo count matches export count
│   ├── listing status (active/pending/sold)
│   └── days on market vs. area median
│
└── Market Signal      (15%)  ← RESO + PerformanceEvent
    ├── price change frequency (fewer = stable = healthy)
    ├── DOM vs. comparable listings
    └── status progression (active → pending = positive signal)
```

### Default Weights

| Sub-Score | Default Weight | Starter | Pro | Enterprise |
|-----------|---------------|---------|-----|-----------|
| Media Quality | 30% | ✓ | ✓ | ✓ (custom weight) |
| Content Readiness | 20% | ✓ | ✓ | ✓ (custom weight) |
| Pipeline Velocity | 15% | — | ✓ | ✓ (custom weight) |
| Syndication Status | 20% | — | ✓ (1 board) | ✓ (unlimited, custom weight) |
| Market Signal | 15% | — | — | ✓ (custom weight) |

When a sub-score is unavailable for a plan tier, its weight is redistributed proportionally across available sub-scores.

Enterprise tenants may customize weights via `PATCH /settings/health-weights`.

---

## 4. Data Model

### `listing_health_scores` table

Stores the latest health score snapshot per listing. Upserted on each recalculation.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `listing_id` | UUID FK (unique) | One active score per listing |
| `overall_score` | Integer (0–100) | Weighted composite |
| `media_score` | Integer (0–100) | Media Quality sub-score |
| `content_score` | Integer (0–100) | Content Readiness sub-score |
| `velocity_score` | Integer (0–100) | Pipeline Velocity sub-score |
| `syndication_score` | Integer (0–100) | Syndication Status sub-score |
| `market_score` | Integer (0–100) | Market Signal sub-score |
| `weights` | JSONB | Weights used for this calculation |
| `signals_snapshot` | JSONB | Raw signal values at calc time |
| `calculated_at` | DateTime(tz) | When this score was computed |
| `created_at` | DateTime(tz) | Row creation |

### `health_score_history` table

Rolling 90-day append-only history for trend analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `listing_id` | UUID FK | |
| `overall_score` | Integer (0–100) | |
| `media_score` | Integer | |
| `content_score` | Integer | |
| `velocity_score` | Integer | |
| `syndication_score` | Integer | |
| `market_score` | Integer | |
| `calculated_at` | DateTime(tz) | |

Cleanup: a scheduled task prunes rows older than 90 days.

### `idx_feed_configs` table

Per-tenant RESO/IDX connection configuration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `name` | String(255) | Display name (e.g., "CRMLS", "Bright MLS") |
| `base_url` | String(500) | RESO Web API base URL |
| `api_key_encrypted` | String(1000) | Encrypted API key (Fernet) |
| `board_id` | String(100) | MLS board identifier |
| `poll_interval_minutes` | Integer | Default 60 |
| `last_polled_at` | DateTime(tz) | Last successful poll |
| `status` | String(20) | `active`, `error`, `disabled` |
| `created_at` | DateTime(tz) | |

---

## 5. Recalculation Strategy

### Event-Driven (immediate, internal signals)

These pipeline events trigger a health score recalculation:

| Event | Sub-Scores Recalculated |
|-------|------------------------|
| `pipeline.completed` | Media, Content, Velocity |
| `listing.approved` | Velocity |
| `listing.override` | Velocity |
| `export.completed` | Content |

Implementation: the `DistributionAgent` (and other event emitters) emit events; the `HealthScoreAgent` listens via a Temporal activity triggered at the end of the pipeline.

### Periodic (hourly, external signals)

`IdxFeedPoller` runs as a background task (like `OutboxPoller`):
1. For each active `IdxFeedConfig`, poll RESO API for listing updates.
2. Write `PerformanceEvent` records: `idx.status_change`, `idx.dom_update`, `idx.price_change`, `idx.photo_count`.
3. Trigger health score recalculation for affected listings.

---

## 6. API Endpoints

### Health Score

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/listings/{id}/health` | User | Score breakdown + 90-day history |
| GET | `/listings/health/summary` | User | Tenant-wide: avg, distribution, alerts |
| GET | `/admin/health/overview` | Admin | Cross-tenant health stats |

#### `GET /listings/{id}/health` Response

```json
{
  "listing_id": "uuid",
  "overall_score": 82,
  "breakdown": {
    "media_quality": { "score": 88, "weight": 0.30, "details": { "avg_quality": 85, "avg_commercial": 72, "hero_strength": 91, "coverage_pct": 100 } },
    "content_readiness": { "score": 90, "weight": 0.20, "details": { "description": true, "fha_passed": true, "social": true, "flyer": true, "export": true } },
    "pipeline_velocity": { "score": 75, "weight": 0.15, "details": { "elapsed_minutes": 4.2, "review_minutes": 12.0, "override_rate": 0.08, "failures": 0 } },
    "syndication": { "score": 70, "weight": 0.20, "details": { "idx_active": true, "photo_match": 23, "photo_expected": 25, "dom": 14 } },
    "market_signal": { "score": 80, "weight": 0.15, "details": { "price_changes": 0, "dom_vs_median": -3, "status": "active" } }
  },
  "trend": [ { "date": "2026-04-01", "score": 78 }, { "date": "2026-04-07", "score": 82 } ],
  "calculated_at": "2026-04-07T14:30:00Z"
}
```

### IDX Feed Config

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/settings/idx-feed` | User (Pro+) | Create IDX config |
| GET | `/settings/idx-feed` | User | List IDX configs |
| PATCH | `/settings/idx-feed/{id}` | User | Update config |
| DELETE | `/settings/idx-feed/{id}` | User | Remove config |

### Health Weights (Enterprise)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/settings/health-weights` | User | Current weights |
| PATCH | `/settings/health-weights` | User (Enterprise) | Custom weights (must sum to 1.0) |

---

## 7. Alerting

When a listing's health score drops below a configurable threshold, the system:

1. Emits a `health.score.alert` event via the outbox.
2. Delivers a webhook notification (existing `webhook_delivery.py` infrastructure).
3. Sends an email notification to the tenant admin.

### Thresholds

- Global default: alert when score < 60
- Per-tenant override: stored in tenant settings (Pro+)
- Alert cooldown: max 1 alert per listing per 24 hours

---

## 8. Plan Gating

| Feature | Starter | Pro | Enterprise |
|---------|---------|-----|-----------|
| Overall health score (single number) | ✓ | ✓ | ✓ |
| Sub-score breakdown | — | ✓ | ✓ |
| Score trend (90-day history) | — | ✓ | ✓ |
| IDX feed integration | — | 1 board | Unlimited |
| Market Signal sub-score | — | — | ✓ |
| Custom weights | — | — | ✓ |
| Health alerts (webhook + email) | — | ✓ | ✓ |
| Cross-tenant benchmarks (admin) | — | — | ✓ |

---

## 9. Frontend

### Listing Card Badge
- Color-coded health dot: green (80+), yellow (60–79), red (<60)
- Tooltip shows overall score on hover

### Listing Detail — Health Panel
- Horizontal bar chart (or radar chart) showing 5 sub-scores
- 90-day sparkline trend
- Actionable callouts: "Missing exterior shot — add one to improve Media Quality"
- Plan-gated sections show upgrade prompts for locked sub-scores

### Tenant Health Dashboard (`/health`)
- Score distribution histogram across all listings
- Top 5 / Bottom 5 listings by health
- Avg score over time trend line
- IDX feed connection status cards

---

## 10. Migration from `engagement_score.py`

The existing `predict_engagement()` function becomes the `media_score` sub-calculator:

1. Refactor `predict_engagement()` → `calculate_media_score()` in `HealthScoreService`.
2. Update all callers (listing detail API, analytics) to use `HealthScoreService.get_score()`.
3. Keep `predict_engagement()` as a thin wrapper that delegates to `calculate_media_score()` for backward compatibility during transition.
4. Remove the wrapper once all callers are migrated.

---

## 11. Implementation Order

1. Models + migration (`listing_health_scores`, `health_score_history`, `idx_feed_configs`)
2. `HealthScoreService` — sub-score calculators + composite
3. Refactor `engagement_score.py` → media sub-score
4. `HealthScoreAgent` (Temporal activity)
5. Wire into pipeline workflow (after `DistributionAgent`)
6. API endpoints (health read + IDX config CRUD)
7. `IdxFeedPoller` background task
8. Frontend health components
9. Alerting (threshold + webhook + email)
10. Tests (unit + integration)
