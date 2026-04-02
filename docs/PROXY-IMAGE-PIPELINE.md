# Proxy Image Pipeline — Plan

> **Status:** Planned — implement after confirming end-to-end pipeline works
> **Goal:** Generate compressed proxy images for AI analysis, map results back to full-res originals

---

## The Problem

Vision T1/T2 agents download full-resolution photos from S3 (often 3-8MB each) to send to Google Vision / GPT-4V. With 18+ photos this means:
- 90-150MB of S3 downloads per listing
- 10-15 second API latency per image
- Possible timeouts on large photo sets
- Unnecessary API cost (same analysis quality at lower resolution)

## The Solution

Generate a 1024px proxy for each upload during ingestion. Use proxies for all AI analysis. Map results back to originals by asset ID. Use originals for all human-facing outputs.

---

## Pipeline Stage Map: Proxy vs Full-Res

| Stage | Agent | Reads | Writes | Notes |
|-------|-------|-------|--------|-------|
| **Upload** | (API endpoint) | — | Full-res to S3 | No change |
| **Ingestion** | `ingestion.py` | Full-res metadata | **Proxy to S3** | NEW: generate 1024px proxy during dedup |
| **Vision T1** | `vision.py` | **Proxy** | Labels/scores to DB | Google Vision API — proxy is sufficient |
| **Vision T2** | `vision.py` | **Proxy** | Detailed analysis to DB | GPT-4V — proxy sufficient for room/quality analysis |
| **Property Verification** | `property_verification.py` | DB only | DB only | No images needed |
| **Coverage** | `coverage.py` | DB only | DB only | Works on labels/metadata, not pixels |
| **Floorplan** | `floorplan.py` | **Proxy** | Floorplan image to S3 | Proxy sufficient for layout detection |
| **Packaging** | `packaging.py` | DB only | DB only | Selects photos by score, no pixel access |
| **Human Review** | (UI) | **Full-res** (presigned URL) | — | User sees originals for approval |
| **Content** | `content.py` | DB only | Text to DB | Generates descriptions from metadata, not pixels |
| **Brand** | `brand.py` | **Full-res** | Branded images to S3 | Logo overlay needs full resolution |
| **Social Content** | `social_content.py` | DB only | Text to DB | Captions from metadata |
| **Social Cuts** | `social_cuts.py` | **Full-res** | Cropped images to S3 | Needs full-res for platform-specific crops |
| **Photo Compliance** | `photo_compliance.py` | DB only | DB only | Text-based FHA validation |
| **MLS Export** | `mls_export.py` | **Full-res** | Resized (2048px) + zip to S3 | Resizes originals for MLS, not proxies |
| **Watermark** | `watermark.py` | **Full-res** | Watermarked images to S3 | Needs full-res for clean watermark |
| **Video** | `video.py` | **Full-res** | Video to S3 | Kling AI needs high-res for cinematic output |
| **Distribution** | `distribution.py` | DB only | — | Sends links, no pixel access |
| **Learning** | `learning.py` | DB only | DB only | Analytics only |

---

## Summary

| Category | Stages | Image Source |
|----------|--------|-------------|
| **AI Analysis** | Vision T1, Vision T2, Floorplan | **Proxy (1024px)** |
| **Human Viewing** | Review UI, Listing Detail | **Full-res (presigned)** |
| **Output Generation** | Brand, Social Cuts, MLS Export, Watermark, Video | **Full-res** |
| **Text/Metadata Only** | Content, Social Content, Compliance, Coverage, Packaging, Learning, Distribution | **No images** |

---

## Proxy Spec

- **Resolution:** 1024px on longest edge (maintain aspect ratio)
- **Format:** JPEG, quality 80
- **Typical size:** 80-200KB (vs 3-8MB original)
- **S3 path:** `listings/{listing_id}/proxies/{asset_id}.jpg`
- **Generation:** PIL/Pillow in the ingestion agent
- **Lifecycle:** Delete proxies when listing is deleted (data retention cleanup)

---

## Implementation Steps

### Step 1: Add proxy generation to ingestion agent
- After dedup, for each valid asset:
  - Download original from S3
  - Resize to 1024px longest edge with PIL
  - Upload proxy to `listings/{listing_id}/proxies/{asset_id}.jpg`
  - Store `proxy_s3_key` on the Asset model (new column or in metadata)

### Step 2: Update Asset model
- Add `proxy_s3_key: str | null` column (migration 026)
- Or store in existing metadata JSONB to avoid migration

### Step 3: Update Vision T1 agent
- Change `storage.download(asset.file_path)` to `storage.download(asset.proxy_s3_key or asset.file_path)`
- Falls back to full-res if proxy doesn't exist (backward compatible)

### Step 4: Update Vision T2 agent
- Same pattern as T1

### Step 5: Update Floorplan agent
- Same pattern — use proxy for layout detection

### Step 6: Verify no regressions
- Packaging, MLS export, brand, video, social cuts all still use `asset.file_path` (full-res)
- Review UI still uses presigned URLs for full-res
- Thumbnail generation in API still uses full-res

---

## Performance Estimate

**Before (18 photos at 5MB avg):**
- S3 download: 90MB → ~30 seconds
- Google Vision: 18 × 8 sec = ~144 seconds
- Total Vision T1: ~3 minutes

**After (18 photos at 150KB avg proxy):**
- S3 download: 2.7MB → ~1 second
- Google Vision: 18 × 2 sec = ~36 seconds
- Total Vision T1: ~40 seconds

**~4x speedup** on Vision T1 alone.
