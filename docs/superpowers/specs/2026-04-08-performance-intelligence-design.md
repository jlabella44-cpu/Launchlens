# Performance Intelligence — Design Spec

> **Date:** 2026-04-08 | **Status:** Active
> **Depends on:** Phase 3 (health score + IDX feeds), scoring_events table

---

## 1. Overview

Performance Intelligence answers: "Do LaunchLens photo selections lead to better listing outcomes?" It correlates photo quality metrics (VisionResult, PackageSelection, ScoringEvent) with market outcomes (DOM, price changes, status progression) from IDX feeds and PerformanceEvents.

The output is:
- **Per-listing insight cards** — "This listing's photos scored 15% above your average. Similar listings sold 8 days faster."
- **Tenant-level benchmarks** — "Your avg DOM: 22 days. Platform avg: 31 days. Your photo quality: 85th percentile."
- **Marketing claims** — "LaunchLens-optimized listings sell X% faster" backed by aggregate data.
- **Feedback into scoring weights** — top-performing photo traits (room types, quality bands) feed back into PackagingAgent.

---

## 2. Data Model

### `listing_outcomes` table (new)

Materialized outcome snapshot per delivered listing, updated by IDX poller.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `listing_id` | UUID FK (unique) | One row per listing |
| `days_on_market` | Integer | From IDX feed |
| `final_price` | Float | Last known price |
| `original_price` | Float | First price seen |
| `price_change_count` | Integer | Number of price adjustments |
| `status` | String(20) | active, pending, sold, withdrawn |
| `sold_date` | DateTime | When status changed to sold |
| `avg_photo_quality` | Float | Avg quality_score of selected photos |
| `avg_commercial_score` | Float | Avg commercial_score of selected photos |
| `hero_quality` | Float | Hero photo's quality score |
| `coverage_pct` | Float | % of required shots present |
| `photo_count` | Integer | Number of photos in package |
| `room_diversity` | Integer | Distinct room types |
| `override_rate` | Float | % of AI selections overridden |
| `health_score_at_delivery` | Integer | Health score when delivered |
| `updated_at` | DateTime | Last IDX update |
| `created_at` | DateTime | |

### `performance_insights` table (new)

Cached insight computations per tenant, refreshed periodically.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS-scoped |
| `insight_type` | String(50) | dom_comparison, quality_correlation, claim |
| `data` | JSONB | Computed insight payload |
| `sample_size` | Integer | Number of listings in computation |
| `calculated_at` | DateTime | |
| `created_at` | DateTime | |

---

## 3. Correlation Engine

`PerformanceCorrelationService`:

1. **Materialize outcomes** — for each delivered listing with IDX data, compute `listing_outcomes` row from PerformanceEvents + VisionResults + PackageSelections.

2. **Compute correlations** — statistical analysis:
   - Photo quality vs DOM (do higher-quality photos correlate with faster sales?)
   - Coverage completeness vs DOM
   - Hero photo strength vs DOM
   - Override rate vs DOM (does trusting AI lead to better outcomes?)
   - Room diversity vs DOM

3. **Generate insights** — per-tenant comparisons:
   - "Your listings avg 22 DOM vs platform avg 31 DOM"
   - "Listings with hero score >80 sell 6 days faster than those <60"
   - "Your kitchen photo quality is in the 90th percentile"

4. **Generate claims** — aggregate marketing data:
   - "LaunchLens-optimized listings sell X% faster" (requires enough sample size)

---

## 4. API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/analytics/performance` | User | Tenant performance overview |
| GET | `/analytics/performance/listing/{id}` | User | Per-listing insight card |
| GET | `/analytics/performance/correlations` | User | Photo trait → outcome correlations |
| GET | `/admin/performance/claims` | Admin | Platform-wide marketing claims |

---

## 5. Implementation Order

1. `listing_outcomes` + `performance_insights` models + migration
2. `PerformanceCorrelationService` — materialize + correlate + insights
3. API endpoints
4. Frontend dashboard components
5. Wire materialization into IDX poller (after health score recalc)
6. Tests
