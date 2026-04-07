# Session Handoff — 2026-04-07 (Phase 3 Complete)

> **For:** Next session (Phase 4+)
> **Branch:** `main` (all work merged)
> **Last commit:** `27cf98f` — feat: Phase 3 — Listing Health Score (#160)

---

## What Shipped Today

### Phase 3: Listing Health Score (#160)
Composite 0–100 score from 5 automated sub-scores (no manual entry):

| Sub-Score | Weight | Source |
|-----------|--------|--------|
| Media Quality | 30% | VisionResult quality/commercial scores, hero strength, coverage % |
| Content Readiness | 20% | Description, FHA pass, social, brand flyer, export bundles |
| Pipeline Velocity | 15% | Elapsed time, review turnaround, override rate, failures |
| Syndication Status | 20% | IDX/RESO feed presence, photo count match, DOM |
| Market Signal | 15% | Price stability, DOM vs median, status progression |

**Key files added:**
- `src/listingjet/services/health_score.py` — 5 sub-calculators + composite
- `src/listingjet/agents/health_score.py` — Temporal activity (Step 8, non-blocking)
- `src/listingjet/services/idx_feed_poller.py` — background RESO feed poller
- `src/listingjet/api/listing_health.py` — 8 endpoints (health read, IDX CRUD, weights)
- `src/listingjet/models/listing_health_score.py`, `health_score_history.py`, `idx_feed_config.py`
- `alembic/versions/041_health_score_and_idx_feed.py` — 3 tables + RLS
- `frontend/src/components/listings/health-badge.tsx`, `health-panel.tsx`
- `frontend/src/app/health/page.tsx` — tenant health dashboard

**Plan gating:**
- Free/Starter: composite score only
- Active Agent/Pro: full breakdown + 1 IDX board + alerts
- Team/Enterprise: all + custom weights + market signal + unlimited IDX

**Spec:** `docs/superpowers/specs/2026-04-07-phase3-health-score-design.md`
**Plan:** `docs/superpowers/plans/2026-04-07-phase3-health-score.md`

### Also merged today (from other sessions)
- #159 — Phase 2: social features (listing events, notifications, social post hub, connected accounts)
- #161 — fix: deduplicate video photos, drone/exterior room detection
- #158 — feat: log Kling clip cost/duration/failure
- #155–157 — deploy pipeline + FFmpeg + video task fixes

### Test fixes included in Phase 3 merge
Fixed pre-existing failures from Phase 2 merge:
- Listings default to `draft` state → updated all test queries to use `?state=draft`
- Kling `poll_task` returns dict → updated assertion
- Engagement score formula aligned with new media sub-score weights

---

## Current Codebase Stats

| Metric | Count |
|--------|-------|
| Agents | 24 |
| API routers | 35 |
| DB migrations | 40 (through 041) |
| Test files | 123 |
| Models | 27+ |

---

## What's Next: Phase 4+ Roadmap

### Phase 4: Social Direct Publish + Scheduling (PRD Phase 2 deferred item)
The social infrastructure is now in place (Phase 2 social features + connected accounts). Next logical step:
- OAuth integration for Instagram, Facebook, TikTok (currently stubbed)
- Direct publish from Social Post Hub (currently copy-paste + "mark as posted")
- Scheduling: pick a time slot from best-time-to-post config, auto-publish
- **Depends on:** Connected accounts OAuth flow, platform API approvals

### Phase 5: Performance Intelligence (PRD Phase 2 deferred item)
Health Score Phase 3 laid the groundwork with IDX feed integration + PerformanceEvent tracking:
- Link photo selections to listing outcomes (DOM, views, saves)
- "LaunchLens-optimized listings sell X% faster" data claim
- ML model to replace rule-based scoring weights
- **Depends on:** IDX feed data accumulation (needs time in production)

### Phase 6: RESO Web API Vendor Certification (PRD Phase 3 vision)
- Apply for RESO certification
- Implement RESO-compliant data submission for certified MLS boards
- True one-click MLS publish for participating boards
- **Depends on:** RESO application process (external timeline)

### Other deferred items (from PRD + TODO.md)
- Photo compliance scanner (dual export modes UI)
- Image embedding near-duplicate detection
- Property website auto-generation (microsite already exists, needs polish)
- Real-time collaborative review (Figma-style)
- Canva API integration (OAuth stubbed, template rendering works)
- LiDAR room measurement extraction
- White-label brokerage deployment

---

## Known Technical Debt

### From TODO.md
1. **Dual credit systems** — `CreditAccount` (new, with granted/purchased pools) vs `Tenant.credit_balance` (legacy). Need to reconcile or deprecate one.
2. **Listings monolith** — `listings_core.py` + `listings_media.py` + `listings_workflow.py` total 800+ lines. Already split into 3 files but could use further decomposition.
3. **Pipeline status endpoint** — `predict_engagement()` runs on every request. Now superseded by cached `ListingHealthScore` — should migrate callers to read from the health score table instead.
4. **CSP blocks frontend** — Content-Security-Policy conflicts with inline styles (Tailwind) and Three.js. Needs CSP nonce strategy.

### Migration chain note
Migration 039 had a `down_revision` mismatch (referenced filename instead of revision ID). Fixed in Phase 3 merge — watch for similar issues if adding migrations.

### Health Score TODOs (marked in code)
- `IdxFeedConfig.api_key_encrypted` — currently stored as plaintext. Add Fernet encryption before production.
- Custom health weights — Enterprise endpoint exists but weights aren't persisted yet (returns requested weights, doesn't save). Need a `tenant_health_config` table or use `Tenant.metadata_`.
- History cleanup — 90-day rolling history needs a scheduled cleanup task (not yet implemented).

---

## Environment Notes

- Python 3.12 required (CI uses 3.12, local dev needs matching)
- All new tiers: `free`, `lite`, `active_agent`, `team` (legacy aliases: `starter`, `pro`, `enterprise` still work)
- Default billing model is `credit` — new listings start as `DRAFT`, credits deducted at pipeline start (not creation)
- IDX feed poller runs alongside outbox poller in FastAPI lifespan

---

## File Map for Key Phase 3 Components

```
src/listingjet/
  models/
    listing_health_score.py    # Latest score snapshot (upserted)
    health_score_history.py    # 90-day rolling history
    idx_feed_config.py         # Per-tenant RESO connection
  services/
    health_score.py            # 5 sub-calculators + composite + get/trend
    idx_feed_poller.py         # Background RESO feed polling
    engagement_score.py        # Thin wrapper → delegates to health_score media calc
  agents/
    health_score.py            # Temporal activity (Step 8 in pipeline)
  api/
    listing_health.py          # All health + IDX + weights endpoints
    schemas/health.py          # Pydantic models
  workflows/
    listing_pipeline.py        # Step 8: run_health_score (non-blocking)

frontend/src/
  components/listings/
    health-badge.tsx           # Green/yellow/red score dot
    health-panel.tsx           # Sub-score bars + trend on listing detail
  app/health/page.tsx          # Tenant health dashboard

alembic/versions/
  041_health_score_and_idx_feed.py  # 3 tables + RLS

tests/
  test_services/test_health_score.py   # 14 unit tests
  test_agents/test_health_score.py     # 2 agent tests
  test_api/test_health.py              # 6 API tests
```
