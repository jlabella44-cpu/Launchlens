# LaunchLens: Listing Media OS — Design Spec

**Date:** 2026-03-27
**Status:** Draft — awaiting user review
**Scope:** PRD rewrite (positioning, pricing copy, onboarding flow) + new agents (MLS Export, Social Content) + export endpoint + Temporal workflow changes + MLS compliance strategy

---

## 1. Positioning Reframe

### From → To

| Surface | Old Framing | New Framing |
|---|---|---|
| Tagline | "AI-powered photo curation platform" | "The operating system for listing media — from raw photos to live on every channel in 3 minutes" |
| Product name context | LaunchLens (a tool) | LaunchLens (a media OS) |
| Feature language | Photo Intelligence, Smart Package, Content Creation | AI Media Engine, Auto-Curation, AI Copywriter |
| Value prop | "We curate your photos" | "We replace your entire listing prep workflow" |

### Pricing Page Copy

Same tiers, same prices, same enforcement logic (`plan_limits.py` unchanged). Only the customer-facing copy changes.

| | Starter ($49/mo) | Pro ($99/mo) | Enterprise (Custom) |
|---|---|---|---|
| **Headline** | "Launch listings faster" | "Your AI marketing team" | "Listing ops at scale" |
| **Hero feature** | AI Photo Curation + MLS Export | Full Media OS (photos + descriptions + social) | White-label Media OS + API |
| **CTA** | "Start free trial" | "Start free trial" | "Talk to sales" |
| **Social proof** | "Used by 50+ photographers" | "Saves teams 100+ hours/month" | "Trusted by top brokerages" |

### Feature Renaming

| Internal Name | Customer-Facing Name | Tier |
|---|---|---|
| Photo Intelligence (Vision + Coverage) | AI Media Engine | All |
| Smart Package (PackagingAgent) | Auto-Curation | All |
| Content Creation (ContentAgent) | AI Copywriter | All |
| Brand Kit (BrandAgent) | Brand Identity System | All |
| MLS Export (MLSExportAgent) | One-Click MLS Export | All |
| Social Posts (SocialContentAgent) | Social Media Studio | Pro+ |
| Learning Engine (LearningAgent) | Adaptive Intelligence | Pro+ |
| Plan Enforcement | Usage dashboard | All (visible) |

---

## 2. Onboarding Flow — Results-First

### Principle

Show the pipeline's value on the user's own photos before asking for account creation or payment.

### Flow

```
Landing page → Drop photos (no auth) → Watch Phase 1 pipeline →
See curated results (watermarked) → "Unlock full package" CTA →
Register → Demo converts to real listing → Phase 2 runs → First listing free
```

### Step 1: Upload (No Auth)

- Landing page hero has a prominent dropzone: "Drop your listing photos — see the AI work in 60 seconds"
- Accepts 5-50 photos, no account required
- This is a demo pipeline run — same agents, results watermarked and ephemeral (24h TTL)

### Step 2: Watch the Pipeline

- Real-time progress visualization (PipelineVisualizer 3D component from frontend plan)
- Each stage animates as it completes: Upload → Analyzing → Curating → Done
- Results page shows: curated photo grid (top 25), hero photo highlighted, coverage card, quality scores

### Step 3: "Unlock the Full Package"

- CTA below results: "Create your account to unlock descriptions, social posts, branded flyers, and MLS export"
- Register/login → lands on the same listing with full pipeline results unlocked
- Brand kit setup prompt: "Upload your logo and colors to generate branded materials" (skippable — uses LaunchLens defaults)

### Step 4: First Real Listing

- Demo listing converts to a real listing (no re-upload needed)
- Full Phase 2 pipeline runs: Content → Brand → Social → Export
- User sees the complete MLS + Marketing bundles
- "Your first listing is free. Choose a plan to keep going."

### Backend: Demo Pipeline

**Model changes:**
- New `ListingState` enum value: `DEMO`
- New fields on `Listing`: `is_demo` (bool, default False), `demo_expires_at` (datetime, nullable)
- Demo listings have `tenant_id = NULL` until claimed

**New router: `api/demo.py`**

| Endpoint | Auth | Description |
|---|---|---|
| `POST /demo/upload` | None | Multipart photos (5-50). Creates demo listing, triggers Phase 1 only. Rate limited: 3/IP/day via Redis. |
| `GET /demo/{id}` | None | Returns curated results. Photos watermarked. Content/brand/social fields return `null` with `"locked": true`. |
| `POST /demo/{id}/claim` | Required | Assigns `tenant_id`, clears `is_demo`, removes expiry. Triggers Phase 2. Returns `ListingResponse`. |

**Watermarking:** Pillow overlay ("LaunchLens Preview" diagonal) applied at read time on the `GET /demo/{id}` endpoint, not stored. Claiming removes it instantly.

**Cleanup:** Temporal cron workflow runs hourly, deletes unclaimed demo listings + S3 assets past `demo_expires_at`.

**Rate limiting:** Uses existing Redis token bucket (`rate_limiter.py`). Key: `demo:{ip}`, limit: 3/day.

---

## 3. MLS Export Agent

### Purpose

Takes an approved listing package and produces two downloadable ZIP bundles: one MLS-compliant (unbranded), one marketing (full branded).

### Inputs

- `listing_id` (state must be `APPROVED`)
- `PackageSelection` records (curated photo set)
- `VisionResult` records (room labels, quality scores)
- `ContentAgent` output (listing description — both MLS-safe and marketing tones)
- `BrandAgent` output (flyer PDF)
- `SocialContentAgent` output (social captions — Pro+ only)

### Processing Steps

#### MLS Package (all tiers)

1. **Photo preparation:** Download originals from S3, resize to MLS max (2048px longest edge, JPEG quality 85, <5MB), strip ALL EXIF data (GPS, camera info — privacy)
2. **Branding strip:** Verify no brand overlays on photos. (Phase 2: photo compliance scanner detects visible branding/signs/people)
3. **Naming:** `{position:02d}_{room_label}_{listing_id[:8]}.jpg` → e.g., `01_exterior_front_a3b2c1d4.jpg`
4. **Metadata CSV:** `filename, position, room_label, quality_score, caption, hero` — one row per photo
5. **MLS-safe description:** `description_mls.txt` — no agent promotion, no personality, strict FHA compliance
6. **Manifest:** `manifest.json` — listing metadata, photo count, timestamp, LaunchLens version, `mode: "mls"`
7. **ZIP:** `{address_slug}_{date}_mls.zip` → S3

#### Marketing Package (all tiers, contents vary by plan)

Everything in MLS Package, plus:
1. **Full description:** `description.txt` — marketing tone with personality
2. **Branded flyer:** `flyer.pdf` — from BrandAgent
3. **Social captions (Pro+):** `social_posts.json` — Instagram + Facebook captions from SocialContentAgent
4. **Manifest:** `mode: "marketing"`, `includes_social: true/false`
5. **ZIP:** `{address_slug}_{date}_marketing.zip` → S3

### State Transition

`APPROVED` → `EXPORTING` → `DELIVERED`

### DB Changes

- `Listing`: add `mls_bundle_path` (S3 key), `marketing_bundle_path` (S3 key)
- `ListingState` enum: add `EXPORTING`

### Error Handling

- Photo download/resize failure: skip + log warning event. Don't fail the bundle.
- <50% of selected photos succeed: fail export, revert state to `APPROVED`
- S3 upload failure: retry 2x, then fail with event

### Dependencies

- `StorageService` (existing) for S3
- `Pillow` (new) for photo resizing + EXIF stripping
- No external API calls

---

## 4. Social Content Agent

### Purpose

Generates platform-specific social media captions from listing data. Instagram + Facebook to start. LinkedIn + Twitter/X deferred.

### Inputs

- `listing_id` (state must be `APPROVED`)
- `Listing` metadata (address, bedrooms, bathrooms, sqft, price)
- Hero photo `VisionResult` (room label, quality descriptors)
- `ContentAgent` marketing description (source material, not copied verbatim)

### Processing

1. **Build prompt context:** Property metadata + hero analysis + description summary
2. **Single Claude call** via existing `ClaudeProvider` with structured JSON output:

```json
{
  "instagram": {
    "caption": "...",
    "hashtags": ["#justlisted", "#realestate", "..."],
    "cta": "Link in bio for details"
  },
  "facebook": {
    "caption": "...",
    "cta": "Schedule a showing today"
  }
}
```

3. **Platform conventions enforced in prompt:**
   - **Instagram:** 2200 char max, 20-30 hashtags in comment block (not inline), emoji-friendly, lifestyle tone, CTA to "link in bio"
   - **Facebook:** 500 char target, no hashtag blocks, conversational/neighborhood tone, direct CTA with link placeholder

4. **FHA compliance filter:** Same `fha_check` service as ContentAgent. Reject and retry on violation (max 2 retries).

5. **Store results:** New `SocialContent` model

### DB Changes

New model: `SocialContent`

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK → Tenant, RLS-scoped |
| listing_id | UUID | FK → Listing |
| platform | String | `"instagram"` or `"facebook"` |
| caption | Text | Generated caption |
| hashtags | JSON | Array of strings (Instagram only, null for Facebook) |
| cta | String | Call-to-action text |
| created_at | DateTime | Auto |

Follows `TenantScopedModel` pattern. RLS policy in migration.

### Plan Gating

Pro+ only. Starter tier: workflow skips this agent entirely. Marketing bundle omits `social_posts.json`.

### Error Handling

Same pattern as ContentAgent: max 2 retries on FHA violation, emit warning event if still failing, continue pipeline (social posts are non-critical — bundle ships without them).

---

## 5. Export API Endpoint

### Endpoint

`GET /listings/{id}/export?mode={mls|marketing}`

**Default mode:** `marketing`

### Behavior

| Condition | Response |
|---|---|
| Bundle exists for requested mode | 200 — presigned S3 URL (1h expiry) + metadata |
| Listing is APPROVED but export hasn't run | 404 — "Export not yet generated" |
| Listing not in APPROVED/EXPORTING/DELIVERED state | 409 — "Listing must be approved before export" |
| User not in listing's tenant | 403 (RLS enforced) |

### Response Shape

```json
{
  "listing_id": "uuid",
  "mode": "mls",
  "download_url": "https://s3...presigned",
  "expires_at": "2026-03-27T15:00:00Z",
  "bundle": {
    "photo_count": 25,
    "includes_description": true,
    "includes_flyer": false,
    "includes_social_posts": false,
    "size_bytes": 48234567,
    "generated_at": "2026-03-27T14:00:00Z"
  }
}
```

### Schema

New Pydantic models in `api/schemas/listings.py`:
- `ExportMode` enum: `mls`, `marketing`
- `BundleMetadata` model
- `ExportResponse` model

### Router

Added to existing `api/listings.py` alongside other listing endpoints. Uses `get_current_user` + `get_current_tenant` deps (existing).

---

## 6. Temporal Workflow Changes

### Current Phase 2

```
ContentAgent → BrandAgent → DistributionAgent (stub)
```

### New Phase 2

```
ContentAgent (both tones) → [BrandAgent + SocialContentAgent] (parallel) → MLSExportAgent → DistributionAgent
```

### Implementation

1. `ContentAgent` makes a **single Claude call** with structured JSON output requesting both tones: `mls_safe` (strict, no agent promotion, no personality) and `marketing` (full branding, personality). Both descriptions are stored as separate columns on a new `ListingContent` row (or as a JSON field on the existing content output — implementation decides, but both tones must be retrievable by MLSExportAgent).

2. After ContentAgent, `BrandAgent` and `SocialContentAgent` run in parallel via `asyncio.gather` on their Temporal activities.

3. After both complete, `MLSExportAgent` runs — it has all inputs needed to build both bundles.

4. `DistributionAgent` remains the final step — marks `DELIVERED`, emits `pipeline.completed`.

### Plan-Aware Branching

Workflow checks tenant plan tier before Phase 2 parallel group:
- **Starter:** `asyncio.gather(brand_activity)` — SocialContentAgent skipped
- **Pro/Enterprise:** `asyncio.gather(brand_activity, social_content_activity)`

### New Activities (`activities/pipeline.py`)

- `run_social_content` — wraps SocialContentAgent
- `run_mls_export` — wraps MLSExportAgent

Added to `ALL_ACTIVITIES` list and Temporal worker registration.

### State Machine Update

```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED → EXPORTING → DELIVERED
```

New state: `EXPORTING` (during MLSExportAgent only). SocialContentAgent runs while state is still `APPROVED`.

Demo additions:
```
DEMO → (claimed) → UPLOADING → ... (normal flow)
DEMO → (expired) → deleted by cleanup
```

---

## 7. MLS Compliance Strategy

### Phase 1 (NOW) — Fully Safe

Our current design is MLS-compliant:
- Export **unbranded** MLS-ready photo bundles (ZIP with correct specs)
- Generate branded content **separately** (flyers, social) — never touches MLS package
- Agent **manually uploads** to MLS — LaunchLens is a prep tool, not an MLS integration
- Clear UX distinction: **"MLS Package"** (unbranded, spec-compliant) vs **"Marketing Package"** (branded, full content)

### Phase 2 — Planned Additions (Deferred, Not Built Now)

- **Two export modes** already designed into the MLSExportAgent (Section 3)
- **Photo compliance scanner:** Detect visible branding, signs, people in uploaded photos before MLS packaging. Similar to Restb.ai. Flag violations for photographer correction.
- **AI description toggle:** "MLS-safe" (no agent promotion, strict FHA) vs "Marketing" (full branding, personality). Already designed into ContentAgent dual-tone output (Section 6).

### Phase 3 — Future (Vision Only)

- **RESO Web API vendor certification** — become a certified Add/Edit vendor
- **Per-MLS partnerships** — start with 2-3 large MLSs (Stellar, Bright, SDMLS)
- **No browser automation — ever.** RESO API route is slower to certify but legally safe and scalable.

### Key Principle

LaunchLens is a **listing prep tool** in Phase 1. We package and optimize — the agent clicks "upload" in their MLS. This is fully compliant and requires zero MLS permissions.

---

## 8. New Dependencies

| Dependency | Purpose | Used By |
|---|---|---|
| `Pillow` | Photo resizing, EXIF stripping, watermarking | MLSExportAgent, demo watermark |

No other new external dependencies. SocialContentAgent uses existing `ClaudeProvider`. MLSExportAgent uses existing `StorageService`.

---

## 9. DB Migration Summary

New migration (005):

**New model:**
- `SocialContent` (id, tenant_id, listing_id, platform, caption, hashtags, cta, created_at) + RLS policy

**Listing table changes:**
- Add `mls_bundle_path` (String, nullable)
- Add `marketing_bundle_path` (String, nullable)
- Add `is_demo` (Boolean, default False)
- Add `demo_expires_at` (DateTime, nullable)

**ListingState enum changes:**
- Add `EXPORTING`
- Add `DEMO`

---

## 10. What Does NOT Change

- Existing agents (Ingestion, Vision, Coverage, Packaging, Content, Brand, Learning)
- Auth system (JWT, register, login, roles)
- Stripe billing (checkout, portal, webhooks)
- Plan enforcement logic (`plan_limits.py` — same tiers, same limits)
- Admin dashboard (tenant/user CRUD, platform stats)
- Docker Compose, CI/CD pipelines
- Database RLS architecture
- Provider ABCs and factory pattern

---

## 11. File Inventory

### New Files

| File | Purpose |
|---|---|
| `src/launchlens/agents/social_content.py` | SocialContentAgent |
| `src/launchlens/agents/mls_export.py` | MLSExportAgent |
| `src/launchlens/models/social_content.py` | SocialContent model |
| `src/launchlens/api/demo.py` | Demo upload/view/claim endpoints |
| `src/launchlens/api/schemas/demo.py` | Demo request/response schemas |
| `alembic/versions/005_social_content_export_demo.py` | Migration |
| `tests/test_agents/test_social_content.py` | SocialContentAgent tests |
| `tests/test_agents/test_mls_export.py` | MLSExportAgent tests |
| `tests/test_api/test_demo.py` | Demo endpoint tests |
| `tests/test_api/test_export.py` | Export endpoint tests |

### Modified Files

| File | Change |
|---|---|
| `src/launchlens/models/listing.py` | Add `mls_bundle_path`, `marketing_bundle_path`, `is_demo`, `demo_expires_at`, `EXPORTING`+`DEMO` states |
| `src/launchlens/agents/content.py` | Dual-tone output (mls_safe + marketing) |
| `src/launchlens/activities/pipeline.py` | Add `run_social_content`, `run_mls_export` activities |
| `src/launchlens/workflows/listing_pipeline.py` | Phase 2 parallel group, plan-aware branching |
| `src/launchlens/workflows/worker.py` | Register new activities |
| `src/launchlens/api/listings.py` | Add `GET /listings/{id}/export` endpoint |
| `src/launchlens/api/schemas/listings.py` | Add `ExportMode`, `BundleMetadata`, `ExportResponse` |
| `src/launchlens/main.py` | Register demo router |
| `src/launchlens/middleware/tenant.py` | Add `/demo/*` to `_PUBLIC_PATHS` |
| `src/launchlens/models/__init__.py` | Export SocialContent |
| `src/launchlens/providers/base.py` | No change needed (ClaudeProvider already supports structured output) |
