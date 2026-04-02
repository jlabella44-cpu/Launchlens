# ListingJet — Temporal Pipeline Execution Guide

> Reference document for understanding the full AI listing pipeline from photo upload to delivery.

---

## How the Pipeline Works

The pipeline runs in **2 phases** separated by a human review gate. A Temporal workflow orchestrates 13 sequential/parallel activities, each backed by a specialized AI agent.

```
USER UPLOADS PHOTOS
        │
        ▼
┌─────────────────────────────────────────────────┐
│  PHASE 1: Analysis Pipeline (Sequential)        │
│                                                 │
│  1. Ingestion (dedup)          → ANALYZING      │
│  2. Vision Tier 1 (Google)     ─┐               │
│     Property Verification      ─┘ (parallel)    │
│  3. Vision Tier 2 (GPT-4V)                      │
│  4. Coverage Analysis                           │
│  5. Floorplan (3D scene)                        │
│  6. Packaging (hero + top 25)  → AWAITING_REVIEW│
│                                                 │
│  VIDEO GENERATION runs in parallel (non-blocking)│
└─────────────────────────────────────────────────┘
        │
        ▼
   ┌─────────────┐
   │ HUMAN REVIEW │  ← Workflow pauses here
   │  (approve)   │  ← Signal resumes it
   └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  PHASE 2: Post-Approval Pipeline (Sequential)   │
│                                                 │
│  7. Content (Claude descriptions)               │
│  8. Brand + Social Content     (parallel)       │
│  9. Chapters (video markers)                    │
│ 10. Social Cuts (platform videos)               │
│ 11. MLS Export (ZIP bundles)   → EXPORTING      │
│ 12. Distribution               → DELIVERED      │
│ 13. Learning (update weights)                   │
└─────────────────────────────────────────────────┘
```

---

## State Machine

```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → [approve] → EXPORTING → DELIVERED
                                                                  ↘ FAILED (on error)
                                                CANCELLED (user cancels)
```

---

## Startup Logs (Worker Boot)

```
[worker.py] INFO  Health check server listening on port 8081
[worker.py] INFO  Temporal TracingInterceptor enabled
[worker.py] INFO  Created schedule: demo-cleanup-hourly
[worker.py] INFO  Created schedule: baseline-aggregation-weekly
[worker.py] INFO  Worker ready — connected to Temporal at temporal:7233
```

---

## Trigger: User Uploads Photos

**API:** `POST /listings/{id}/assets` → state becomes `UPLOADING`

**Temporal:** Starts workflow `listing-pipeline-{listing_id}` on queue `listingjet-main`

---

## Phase 1: Analysis Pipeline

### Step 1: Ingestion

| | |
|---|---|
| **Activity** | `run_ingestion` → `IngestionAgent` |
| **Timeout** | 10 min, 3 retries |
| **State** | → `ANALYZING` |
| **Event** | `ingestion.completed` `{ingested_count, duplicate_count}` |
| **What it does** | Deduplicates assets by SHA-256 file hash. Marks duplicates as `state=duplicate`, keeps unique ones as `state=ingested`. |

### Step 2: Vision Tier 1 + Property Verification (Parallel)

| | |
|---|---|
| **Activity** | `run_vision_tier1` + `run_property_verification` |
| **Timeout** | 10 min / 2 min |
| **Event** | `vision.tier1.completed` `{asset_count}` |
| **What it does** | Google Vision labels every photo → extracts room label, quality score (0-100), commercial score, hero candidate flag. Property verification cross-references address against public records (Zillow, Redfin scrapers). |
| **Cost** | ~$0.02 × photo_count (Google Vision) |

**Vision Tier 1 scoring:**
- `quality_score` = max label confidence × 100
- `commercial_score` = min(100, count_of(natural light, hardwood, granite, stainless steel) × 20)
- `hero_candidate` = quality_score ≥ 70 AND commercial_score ≥ 40

### Step 3: Vision Tier 2

| | |
|---|---|
| **Activity** | `run_vision_tier2` |
| **Timeout** | 20 min |
| **Event** | `vision.tier2.completed` `{candidate_count}` |
| **What it does** | GPT-4V deep analysis on top 20 hero candidates from Tier 1. Refines quality scores, adds hero explanations (why this photo is good). |
| **Cost** | ~$0.03 × candidate_count (GPT-4V) |

### Step 4: Coverage Analysis

| | |
|---|---|
| **Activity** | `run_coverage` |
| **Timeout** | 10 min |
| **Events** | `coverage.gap` / `coverage.mismatch` / `coverage.record_mismatch` |
| **What it does** | Checks photos against 5 required shots: exterior, living room, kitchen, bedroom, bathroom. Reports missing rooms. Compares vision bed/bath counts vs listing metadata. Cross-references with public property records if available. |

**Required shots:** `{exterior, living_room, kitchen, bedroom, bathroom}`

### Step 5: Floorplan

| | |
|---|---|
| **Activity** | `run_floorplan` |
| **Timeout** | 20 min |
| **Event** | `floorplan.completed` `{room_count}` |
| **What it does** | If a floorplan image is detected in assets, GPT-4V extracts room polygons, doors, windows → builds DollhouseScene JSON for 3D viewer. Skips if no floorplan asset found. |
| **Cost** | ~$0.03 (1 GPT-4V call) |

### Step 6: Packaging

| | |
|---|---|
| **Activity** | `run_packaging` |
| **Timeout** | 10 min |
| **State** | → `AWAITING_REVIEW` |
| **Event** | `packaging.completed` `{hero_asset_id, total_selected}` |
| **What it does** | Scores all photos using: quality score + commercial score + tenant learning weights (from past approvals/rejections). Selects top 25 for MLS package (1 hero + 24 supporting). Creates `PackageSelection` rows. Sends review-ready notification email. |

**Scoring formula:** `WeightManager.score(quality_score, commercial_score, hero_candidate, room_weight)`

---

## Video Generation (Parallel, Non-Blocking)

Runs alongside Phase 1 — doesn't block the pipeline:

| | |
|---|---|
| **Activity** | `run_video` |
| **Timeout** | 30 min |
| **Conditions** | Legacy billing: always runs. Credit billing: only if `ai_video_tour` addon purchased. |
| **Event** | `video.completed` `{clip_count, s3_key}` |
| **Cost** | ~$0.50 × clip_count (Kling AI) |

**Video pipeline:**
1. Select up to 8 photos via `SLOT_ORDER` room priority
2. Generate Kling AI video clips (max 3 concurrent, 3s stagger between calls)
3. Download clips to temp files
4. Generate branded end-card from BrandKit (logo, colors, agent name)
5. Stitch all clips with transitions (fade, cross-dissolve)
6. Add voiceover narration via ElevenLabs (from listing description)
7. Upload final MP4 to S3
8. Create `VideoAsset` record

**On failure:** `workflow.logger.warning("video_task_failed listing=%s error=%s", ...)` — pipeline continues without video.

---

## Signal Wait: Human Review

```python
await workflow.wait_condition(lambda: self._review_completed)
```

**Listing is `AWAITING_REVIEW`.** Workflow pauses here indefinitely until signal.

**When user clicks Approve** (`POST /listings/{id}/approve`):
```
temporal_client.signal_review_completed(listing_id)
  → handle.signal(ListingPipeline.human_review_completed)
  → self._review_completed = True
  → Workflow resumes Phase 2
```

---

## Phase 2: Post-Approval Pipeline

### Step 7: Content Generation

| | |
|---|---|
| **Activity** | `run_content` → `ContentAgent` |
| **Timeout** | 10 min |
| **Event** | `content.completed` `{fha_passed, mls_safe_length, marketing_length}` |

**What it does:**
1. Loads top 5 VisionResults for property context
2. Loads brand kit voice samples (if available) for tone matching
3. Reads market context from metadata (buyers_market, hot_market, spring_refresh, investment)
4. Applies tone intensity slider (0-100): utility (0.1 temp) → balanced (0.5) → high_flair (0.8-1.0)
5. Claude generates dual-tone descriptions: MLS-safe + marketing
6. FHA fair housing compliance check — retries with lower temperature if first pass fails

**Returns:** `{mls_safe: str, marketing: str, fha_passed: bool}`

### Step 8: Brand + Social Content (Parallel)

**Brand Agent:**
| | |
|---|---|
| **Event** | `brand.completed` `{flyer_s3_key}` |
| **What it does** | Loads hero photo + brand kit → renders branded flyer via Canva template → uploads PDF to S3 |

**Social Content Agent** (plan-gated):
| | |
|---|---|
| **Conditions** | Legacy: pro/enterprise. Credit: `social_content_pack` addon. |
| **Event** | `social_content.completed` `{platforms, fha_passed}` |
| **What it does** | Claude generates Instagram + Facebook captions (hooks, hashtags, CTAs). FHA compliance check. Stores `SocialContent` rows. |

### Step 9: Chapters

| | |
|---|---|
| **Activity** | `run_chapters` |
| **Event** | `chapter.completed` `{chapter_count}` |
| **What it does** | GPT-4V analyzes video → extracts chapter markers (timestamp, label, description). Skips if no ready video. |

### Step 10: Social Cuts

| | |
|---|---|
| **Activity** | `run_social_cuts` |
| **Event** | `social_cuts.completed` `{cut_count, platforms}` |

**Platform specs:**
| Platform | Resolution | Max Duration |
|---|---|---|
| Instagram | 1080×1920 | 30s |
| TikTok | 1080×1920 | 60s |
| Facebook | 1920×1080 | 60s |
| YouTube Shorts | 1080×1920 | 60s |

Uses FFmpeg: scale/pad → trim → encode with libx264

### Step 11: MLS Export

| | |
|---|---|
| **Activity** | `run_mls_export` |
| **Timeout** | 15 min |
| **State** | → `EXPORTING` |
| **Event** | `mls_export.completed` `{mls_bundle_path, marketing_bundle_path, photo_count}` |

**Builds two ZIP bundles:**

| Bundle | Contents |
|---|---|
| **MLS** | Resized photos (max 2048px, JPEG 85%) + metadata.csv + mls_description.txt + manifest.json |
| **Marketing** | Everything in MLS + marketing description + flyer PDF + social posts JSON |

### Step 12: Distribution

| | |
|---|---|
| **Activity** | `run_distribution` |
| **State** | → `DELIVERED` |
| **Event** | `pipeline.completed` `{listing_id}` |
| **What it does** | Sets final state. Records performance event. Sends listing-delivered email to tenant admin with download link. |

### Step 13: Learning

| | |
|---|---|
| **Activity** | `run_learning` |
| **Event** | `learning.completed` `{weights_updated}` |
| **What it does** | Reads human override events (photo approvals, rejections, swaps during review). Updates per-tenant `LearningWeight` records so future listings score photos better. |

---

## Workflow Complete

```python
return f"pipeline_complete:{listing_id}"
```

**Final state: `DELIVERED`**

---

## All Events (Chronological)

| Event | Agent | When |
|---|---|---|
| `ingestion.completed` | Ingestion | After dedup |
| `vision.tier1.completed` | Vision | After Google Vision |
| `vision.tier2.completed` | Vision | After GPT-4V deep pass |
| `coverage.gap` | Coverage | If missing required shots |
| `coverage.mismatch` | Coverage | If bed/bath count mismatch |
| `coverage.record_mismatch` | Coverage | If public records disagree |
| `floorplan.completed` | Floorplan | After 3D scene built |
| `packaging.completed` | Packaging | After hero + package selected |
| `video.completed` | Video | After video stitched + uploaded |
| `content.completed` | Content | After descriptions generated |
| `brand.completed` | Brand | After flyer rendered |
| `social_content.completed` | Social | After captions generated |
| `chapter.completed` | Chapters | After video chapters extracted |
| `social_cuts.completed` | Social Cuts | After platform cuts created |
| `mls_export.completed` | MLS Export | After ZIP bundles uploaded |
| `pipeline.completed` | Distribution | Final — listing delivered |
| `learning.completed` | Learning | After weights updated |

---

## Timeouts & Retries

| Activity | Timeout | Retries |
|---|---|---|
| ingestion, vision_t1, coverage, packaging, content, brand, distribution, learning, chapters, social_cuts, social_content | 10 min | 3 |
| property_verification | 2 min | 3 |
| vision_t2, floorplan | 20 min | 3 |
| mls_export | 15 min | 3 |
| video | 30 min | 3 |

---

## Estimated Costs Per Listing

| Provider | Per-Call Cost | Typical Calls | Est. Total |
|---|---|---|---|
| Google Vision (Tier 1) | $0.02 | ~30 photos | ~$0.60 |
| GPT-4V (Tier 2) | $0.03 | ~20 candidates | ~$0.60 |
| GPT-4V (Floorplan) | $0.03 | 1 | ~$0.03 |
| Claude (Content) | $0.05 | 1-2 (+ FHA retry) | ~$0.10 |
| Kling AI (Video) | $0.50 | ~6 clips | ~$3.00 |
| GPT-4V (Chapters) | $0.03 | 1 | ~$0.03 |
| **Total per listing** | | | **~$4.36** |

---

## Cron Workflows

| Schedule | Workflow | What it does |
|---|---|---|
| Hourly | `DemoCleanupWorkflow` | Deletes expired demo listings + S3 assets |
| Weekly | `BaselineAggregationWorkflow` | Averages learning weights across all tenants per room label → updates global baseline (requires ≥3 tenants per label) |

---

## Key Log Lines to Watch

### Normal Operation
```
INFO  Health check server listening on port 8081
INFO  Worker ready — connected to Temporal at temporal:7233
INFO  Created schedule: demo-cleanup-hourly
INFO  Created schedule: baseline-aggregation-weekly
```

### Warnings (Non-Fatal)
```
WARNING  video_task_failed listing=<id> error=<exc>     # Video failed, pipeline continues
WARNING  voiceover_failed listing=<id>                   # Voiceover failed, video keeps raw audio
WARNING  Failed to create schedule <id>: <exc>           # Schedule creation failed (retryable)
```

### Errors (Investigate)
```
EXCEPTION  Pipeline trigger failed for listing <id>      # Temporal unreachable
EXCEPTION  listing_delivered email failed for listing <id> # SMTP failure
ERROR      Error during shutdown: <exc>                   # Worker shutdown issue
WARNING    Shutdown timeout reached — forcing exit        # Activities didn't finish in 30s
```

---

## Worker Health Endpoints

| Endpoint | Returns | Meaning |
|---|---|---|
| `GET :8081/health` | 200 `{"status": "ok"}` | Worker connected and polling |
| `GET :8081/health` | 503 `{"status": "starting"}` | Still connecting to Temporal |
| `GET :8081/health` | 503 `{"status": "shutting_down"}` | Graceful shutdown in progress |
| `GET :8081/ready` | 200 `{"status": "ready"}` | Temporal connection established |
| `GET :8081/ready` | 503 `{"status": "not_ready"}` | Not yet connected |
