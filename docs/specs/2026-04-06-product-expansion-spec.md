# ListingJet Product Expansion — Phased Roadmap & Phase 1 Spec

**Date:** 2026-04-06
**Status:** Brainstormed, ready for implementation planning

## Context
ListingJet (codebase at `C:\Users\Jeff\launchlens`) is a real estate listing marketing platform. Backend: Python/FastAPI + Temporal workflows on AWS ECS. Frontend: Next.js 15 on Vercel. The user wants a major product expansion covering social features, listing health scoring, review UI improvements, MLS direct upload, and a reworked listing creation flow.

We agreed to **phase this out** into incremental releases. Phase 1 (creation flow + package restructuring) ships first.

---

## Decisions Made (from brainstorming)

### Phasing Strategy
- **Phase 1**: Creation flow rework + package restructuring (FIRST)
- **Phase 2**: Social features (account linking, scheduling, reminders, post types)
- **Phase 3**: Listing Health Score + monitoring (time-on-market, showings, saves)
- **Phase 4**: Review UI overhaul (AI reasoning visibility, agree/disagree, better arrangement)
- **Phase 5**: MLS direct upload (RETS/RESO research, board approval, auto-upload)
- **Phase 6**: Social posting & monitoring (actual posting to linked accounts, analytics)

### Phase 1 Decisions

**Package Restructuring:**
- New base listing cost: **15 credits** (up from 12)
- Base now INCLUDES: social content, social cuts, photo compliance, MLS export, microsite
- Remove social_pack, photo_compliance, social_content_pack from add-on catalog
- Remaining add-ons: AI Video Tour (20 credits), Virtual Staging (15 credits), 3D Floorplan (8 credits)
- NEW "All Add-ons" bundle: **30 credits** (~30% off the 43 individual total)

**Creation Flow (Multi-Step Wizard):**
- Replace current dialog with a full-page multi-step wizard
- Photos uploaded BEFORE confirmation (part of wizard, not after)
- Step 1: Property Details (address + ATTOM autocomplete, beds, baths, sqft, price, type)
- Step 2: Upload Photos (drag-drop, max 50 files, 20MB each, presigned S3 URLs)
- Step 3: Virtual Staging (tag empty rooms for staging — MUST happen pre-pipeline so staged photos flow through all downstream content)
- Step 4: Add-ons (AI Video Tour, 3D Floorplan, individual prices + bundle option. Virtual staging shown here too if not selected in Step 3)
- Step 5: Review & Confirm (summary, total credit cost, "Create Listing" button, pipeline starts immediately)

**Photo Editing Philosophy:**
- Agents upload professionally edited photos — no general AI enhancement needed
- Virtual staging is the key pre-pipeline add-on (empty rooms -> furnished)
- AI Image Editing removed as a separate add-on

**Pipeline Changes:**
- Social content, social cuts, photo compliance now ALWAYS run (no longer addon-gated)
- Virtual staging must run BEFORE packaging so staged photos appear in all downstream material

### Listing Health Score Decisions (Phase 3)
- Composite score representing marketing utilization (IDX, media, engagement)
- Data sources (layered approach, NO manual entry):
  1. Webhook integrations from showing tools (ShowingTime, Calendly, etc.)
  2. Portal scraping (Zillow, Realtor.com, Redfin) — existing `property_scraper/` service as foundation
  3. IDX/MLS API feeds where available (RESO Web API, Spark, Bridge)
- Track: time on market, number of showings, number of saves on portals

### Other Feature Notes
- Social features: best time to post by platform/day, post types by listing event (live, open house, price change, sold/pending), option to auto-post OR monitor
- Review UI: show AI vision reasoning (GPT-4V analysis), agree/disagree workflow, better photo arrangement
- MLS direct upload: research board-by-board approval process

---

## Phase 1 Implementation Plan

### 1. Backend — Package & Pricing Restructuring

**Files to modify:**
- `/src/listingjet/config/tiers.py` — Update `SERVICE_CREDIT_COSTS`, set base to 15, remove social/compliance add-on costs, add bundle pricing config
- `/src/listingjet/models/addon_purchase.py` — Add bundle support
- `/src/listingjet/services/credits.py` — Add bundle pricing logic, update cost calculation
- `/src/listingjet/services/listing_creation.py` — Update base deduction from 12 -> 15 credits

**New pricing structure:**
```
Base: 15 credits (includes social_content, social_cuts, photo_compliance, mls_export, microsite)
AI Video Tour: 20 credits
Virtual Staging: 15 credits
3D Floorplan: 8 credits
All Add-ons Bundle: 30 credits (video + staging + floorplan, ~30% off)
```

**Backward compatibility:** Existing listings retain their original credit_cost.

### 2. Backend — Pipeline Changes

**Files to modify:**
- `/src/listingjet/workflows/listing_pipeline.py` — Remove addon gates for social_content, social_cuts, photo_compliance. Move virtual_staging BEFORE packaging.
- `/src/listingjet/activities/pipeline.py` — Ensure activity ordering supports staging -> packaging -> content flow

**New activity order (post-approval):**
1. Virtual staging (if addon selected) — NEW POSITION: before packaging
2. Packaging (uses staged photos if available)
3. Brand
4. Content
5. Social content (ALWAYS runs now)
6. Social cuts (ALWAYS runs now)
7. Photo compliance (ALWAYS runs now)
8. Chapters
9. Video (if addon)
10. 3D Floorplan (if addon)
11. MLS export (ALWAYS)
12. Microsite (ALWAYS)
13. Distribution
14. Learning

### 3. Backend — Multi-Step Creation API

**Recommended approach: Multi-endpoint flow**
- `POST /listings` — Create listing with property details (state: DRAFT)
- `POST /listings/{id}/upload-urls` — Get presigned URLs (existing)
- `POST /listings/{id}/staging-tags` — Tag photos for virtual staging (NEW)
- `POST /listings/{id}/addons` — Select add-ons including bundle (update for bundle support)
- `POST /listings/{id}/start-pipeline` — Confirm, deduct credits, start pipeline (NEW)

**New listing state:** Add `DRAFT` before `NEW`. Credits deducted only when pipeline starts.

### 4. Frontend — Multi-Step Wizard

**New files:**
- `/frontend/src/app/listings/new/page.tsx` — Dedicated wizard page
- `/frontend/src/components/listings/creation-wizard/wizard-container.tsx`
- `/frontend/src/components/listings/creation-wizard/step-property-details.tsx`
- `/frontend/src/components/listings/creation-wizard/step-upload-photos.tsx`
- `/frontend/src/components/listings/creation-wizard/step-virtual-staging.tsx`
- `/frontend/src/components/listings/creation-wizard/step-addons.tsx`
- `/frontend/src/components/listings/creation-wizard/step-review-confirm.tsx`

### 5. Frontend — Bundle UI

- Individual add-on cards with prices
- "Premium Bundle" card: all 3 for 30 credits (save 13)
- Selecting bundle auto-checks all three
- Virtual staging state synced between Step 3 and Step 4

---

## Verification Plan

1. Credit calculation tests for new base price and bundle logic
2. End-to-end listing creation via new wizard
3. Pipeline: social content, social cuts, photo compliance run without addon flags
4. Pipeline: virtual staging runs before packaging when selected
5. Backward compat: existing listings display correctly
6. Credit deduction: 15 base, 30 bundle, correct individual costs
7. DRAFT state: no pipeline trigger or credit deduction until confirmed

---

## Key Files Reference

**Backend:**
- `/src/listingjet/config/tiers.py`
- `/src/listingjet/models/listing.py`
- `/src/listingjet/models/addon_purchase.py`
- `/src/listingjet/models/credit_account.py`
- `/src/listingjet/models/credit_transaction.py`
- `/src/listingjet/api/listings_core.py`
- `/src/listingjet/api/listings_workflow.py`
- `/src/listingjet/api/listings_media.py`
- `/src/listingjet/services/listing_creation.py`
- `/src/listingjet/services/credits.py`
- `/src/listingjet/workflows/listing_pipeline.py`
- `/src/listingjet/activities/pipeline.py`

**Frontend:**
- `/frontend/src/components/listings/create-listing-dialog.tsx`
- `/frontend/src/components/listings/asset-upload-form.tsx`
- `/frontend/src/components/listings/pipeline-status.tsx`
- `/frontend/src/app/listings/[id]/page.tsx`
- `/frontend/src/app/review/page.tsx`
