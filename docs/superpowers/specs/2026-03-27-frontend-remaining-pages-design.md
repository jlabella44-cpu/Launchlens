# Frontend Remaining Pages — Design Spec

**Date:** 2026-03-27
**Scope:** 6 pages/components to complete the LaunchLens frontend

---

## Overview

Add the remaining frontend pages that connect to existing backend endpoints: demo dropzone (public), pricing (public), export download, video player with chapters, video upload form, and social media preview cards.

All pages follow existing patterns: `"use client"` components, `ApiClient` fetch wrapper with JWT, Tailwind CSS 4 + Framer Motion, GlassCard/Button primitives.

---

## New Files

| File | Auth | Description |
|------|------|-------------|
| `src/app/demo/page.tsx` | No | Public drag-and-drop upload → AI results |
| `src/app/demo/[id]/page.tsx` | No | Demo results view + claim CTA |
| `src/app/pricing/page.tsx` | No | Three-tier comparison (Starter/Pro/Enterprise) |
| `src/app/listings/[id]/export/page.tsx` | Yes | MLS vs Marketing toggle + download |
| `src/components/listings/video-player.tsx` | Yes | Video player with chapter timeline |
| `src/components/listings/video-upload.tsx` | Yes | Pro/user video registration form |
| `src/components/listings/social-preview.tsx` | Yes | Platform-specific cut preview cards |

## Modified Files

| File | Changes |
|------|---------|
| `src/lib/types.ts` | Add VideoResponse, SocialCut, DemoUploadResponse, DemoViewResponse types |
| `src/lib/api-client.ts` | Add methods: demoUpload, demoView, getVideo, getSocialCuts, uploadVideo |
| `src/app/listings/[id]/page.tsx` | Integrate VideoPlayer, VideoUpload, SocialPreview sections |
| `src/app/layout.tsx` | Exclude `/demo` and `/pricing` from ProtectedRoute |
| `src/components/layout/nav.tsx` | Add Pricing link |

---

## Page Designs

### 1. Demo Dropzone (`/demo`)

- **No auth required.** Public landing page.
- Hero: tagline "From raw listing media to launch-ready marketing in minutes."
- Large drag-and-drop zone with dashed border, glassmorphism backdrop
- Accepts image file paths (S3 keys in MVP — actual file upload is Phase 2)
- Calls `POST /demo/upload` with `{ s3_keys: [...], address: {...} }`
- Shows loading animation during pipeline processing
- Redirects to `/demo/{id}` on completion

### 2. Demo Results (`/demo/[id]`)

- **No auth required.**
- Calls `GET /demo/{id}` — shows AI-curated photo package
- Displays scored photos in a grid with room labels and quality scores
- CTA: "Claim these results" → redirects to `/register` with `?claim={id}` param
- After registration, calls `POST /demo/{id}/claim`

### 3. Pricing (`/pricing`)

- **No auth required.**
- Three GlassCard columns: Starter ($29/mo), Pro ($99/mo), Enterprise ($299/mo)
- Feature comparison rows matching PLAN_LIMITS:
  - Listings/month: 5 / 50 / 500
  - Assets/listing: 25 / 50 / 100
  - Tier-2 Vision (GPT-4V): ❌ / ✅ / ✅
  - Social Content: ❌ / ✅ / ✅
  - AI Video Tours: ❌ / ✅ / ✅
- Pro tier visually highlighted (recommended badge, accent border)
- CTA buttons: "Get Started" → `/register?plan={tier}`

### 4. Export Download (`/listings/[id]/export`)

- **Auth required.**
- Two-mode toggle: MLS (unbranded) vs Marketing (branded + social)
- Bundle contents summary per mode:
  - MLS: photos (unbranded), description (MLS-safe)
  - Marketing: photos (branded), description (marketing tone), flyer, social posts
- Download button calls `GET /listings/{id}/export?mode={mls|marketing}`
- Opens presigned S3 URL in new tab
- Framer Motion spring animation on toggle switch

### 5. Video Player (`video-player.tsx`)

- Component, used on listing detail page
- Native `<video>` element with controls
- Video type badge: "AI Generated" / "Professional" / "User Upload"
- Chapter timeline below video: clickable markers with room labels
- Clicking a chapter marker seeks video to that timestamp
- Poster thumbnail from `thumbnail_s3_key` (falls back to first frame)
- Fetches data from `GET /listings/{id}/video`

### 6. Video Upload (`video-upload.tsx`)

- Component, used on listing detail page
- Shows when no video exists or as "Add Video" action
- Form fields:
  - S3 key input (text field — file picker is Phase 2)
  - Video type: radio buttons (Professional / User Submitted)
  - Duration (optional number field)
- Calls `POST /listings/{id}/video/upload`
- On success, shows VideoPlayer component with the new video
- Validates s3_key starts with `videos/{listing_id}/`

### 7. Social Preview Cards (`social-preview.tsx`)

- Component, used on listing detail page below video
- Grid of 4 platform cards (Instagram, TikTok, Facebook, YouTube Shorts)
- Each card shows: platform name/icon, dimensions, max duration, download link
- Download links are S3 presigned URLs (Phase 2 — MVP shows s3_key)
- Fetches from `GET /listings/{id}/video/social-cuts`
- Empty state: "Social cuts will be generated after video processing"

---

## New TypeScript Types

```typescript
interface VideoResponse {
  s3_key: string;
  video_type: "ai_generated" | "user_raw" | "professional";
  duration_seconds: number | null;
  status: string;
  chapters: Chapter[] | null;
  social_cuts: SocialCut[] | null;
  thumbnail_s3_key: string | null;
  clip_count: number | null;
  created_at: string;
}

interface Chapter {
  time: number;
  label: string;
  description: string;
}

interface SocialCut {
  platform: string;
  s3_key: string;
  width: number;
  height: number;
  max_duration: number;
}

interface DemoUploadRequest {
  s3_keys: string[];
  address: Record<string, string>;
}

interface DemoUploadResponse {
  demo_id: string;
  status: string;
}

interface DemoViewResponse {
  id: string;
  status: string;
  address: Record<string, string>;
  package: PackageSelection[];
  created_at: string;
  expires_at: string;
}

interface VideoUploadRequest {
  s3_key: string;
  video_type: "user_raw" | "professional";
  duration_seconds?: number;
}
```

---

## Not In Scope

- Actual file upload (drag-and-drop sends files to S3) — Phase 2, MVP uses S3 key strings
- HLS streaming / CDN player — MVP uses native `<video>` with S3 presigned URLs
- Video analytics (views, watch time)
- Platform-specific social post preview rendering (just metadata cards)
- Demo rate limiting UI (backend handles it, frontend shows error)
