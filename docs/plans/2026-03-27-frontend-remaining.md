# Frontend Remaining Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 remaining pages/components to complete the LaunchLens frontend: demo dropzone, pricing, export download, video player, video upload, and social preview cards.

**Architecture:** All pages follow existing patterns — `"use client"` components, `ApiClient` singleton for data fetching with JWT, Tailwind CSS 4 styling with CSS variables, Framer Motion animations, GlassCard/Button/Badge UI primitives. Public pages (demo, pricing) bypass ProtectedRoute via pathname check in auth-wrapper.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS 4, Framer Motion

**IMPORTANT:** Read `frontend/AGENTS.md` before writing code — Next.js APIs may differ from training data. Check `node_modules/next/dist/docs/` for current conventions.

---

## File Structure

```
frontend/src/
  lib/
    types.ts                        MODIFY — add Video, SocialCut, Demo types
    api-client.ts                   MODIFY — add demo, video, social-cuts methods

  app/
    auth-wrapper.tsx                MODIFY — skip ProtectedRoute for /demo, /pricing
    demo/
      page.tsx                      CREATE — public demo dropzone
      [id]/
        page.tsx                    CREATE — demo results view + claim CTA
    pricing/
      page.tsx                      CREATE — three-tier comparison
    listings/
      [id]/
        page.tsx                    MODIFY — integrate video + social sections
        export/
          page.tsx                  CREATE — MLS vs Marketing download

  components/
    layout/
      nav.tsx                       MODIFY — add Pricing link
    listings/
      video-player.tsx              CREATE — video player + chapter timeline
      video-upload.tsx              CREATE — pro/user video upload form
      social-preview.tsx            CREATE — platform cut preview cards
```

---

## Tasks

---

### Task 1: Types + API client methods

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Add new types to types.ts**

Append to `frontend/src/lib/types.ts`:

```typescript
export interface VideoResponse {
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

export interface Chapter {
  time: number;
  label: string;
  description: string;
}

export interface SocialCut {
  platform: string;
  s3_key: string;
  width: number;
  height: number;
  max_duration: number;
}

export interface VideoUploadRequest {
  s3_key: string;
  video_type: "user_raw" | "professional";
  duration_seconds?: number;
}

export interface VideoUploadResponse {
  id: string;
  s3_key: string;
  video_type: string;
  status: string;
}

export interface DemoUploadRequest {
  file_paths: string[];
}

export interface DemoUploadResponse {
  demo_id: string;
  photo_count: number;
  expires_at: string;
}

export interface DemoViewResponse {
  demo_id: string;
  address: Record<string, string>;
  state: string;
  is_demo: boolean;
  photos: { file_path: string; room_label?: string; quality_score?: number }[];
}
```

- [ ] **Step 2: Add API methods to api-client.ts**

Add import for new types at the top of `frontend/src/lib/api-client.ts`:

```typescript
import type {
  // ... existing imports ...
  VideoResponse,
  SocialCut,
  VideoUploadRequest,
  VideoUploadResponse,
  DemoUploadRequest,
  DemoUploadResponse,
  DemoViewResponse,
} from "./types";
```

Add these methods to the `ApiClient` class, after the existing `getExport` method:

```typescript
  // Video
  async getVideo(listingId: string): Promise<VideoResponse> {
    return this.request<VideoResponse>(`/listings/${listingId}/video`);
  }

  async getSocialCuts(listingId: string): Promise<SocialCut[]> {
    return this.request<SocialCut[]>(`/listings/${listingId}/video/social-cuts`);
  }

  async uploadVideo(listingId: string, data: VideoUploadRequest): Promise<VideoUploadResponse> {
    return this.request<VideoUploadResponse>(`/listings/${listingId}/video/upload`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Demo (no auth required)
  async demoUpload(data: DemoUploadRequest): Promise<DemoUploadResponse> {
    return this.request<DemoUploadResponse>("/demo/upload", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async demoView(id: string): Promise<DemoViewResponse> {
    return this.request<DemoViewResponse>(`/demo/${id}`);
  }

  async demoClaim(id: string): Promise<{ listing_id: string }> {
    return this.request<{ listing_id: string }>(`/demo/${id}/claim`, { method: "POST" });
  }
```

- [ ] **Step 3: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/lib/types.ts frontend/src/lib/api-client.ts && git commit -m "feat(frontend): add Video, Demo, SocialCut types and API methods"
```

---

### Task 2: Public route bypass + nav update

**Files:**
- Modify: `frontend/src/app/auth-wrapper.tsx`
- Modify: `frontend/src/components/layout/nav.tsx`

- [ ] **Step 1: Update auth-wrapper to bypass auth for public routes**

Replace `frontend/src/app/auth-wrapper.tsx` with:

```tsx
"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/contexts/auth-context";
import { ProtectedRoute } from "@/components/layout/protected-route";
import type { ReactNode } from "react";

const PUBLIC_PATHS = ["/login", "/register", "/demo", "/pricing"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export function AuthProviderWrapper({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthProvider>
      {isPublicPath(pathname) ? children : <ProtectedRoute>{children}</ProtectedRoute>}
    </AuthProvider>
  );
}
```

- [ ] **Step 2: Add Pricing link to nav**

In `frontend/src/components/layout/nav.tsx`, add a Pricing link in the nav bar. Replace the content inside `<div className="flex items-center gap-4">`:

```tsx
      <div className="flex items-center gap-4">
        <Link
          href="/pricing"
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
        >
          Pricing
        </Link>
        {user && (
          <>
            <span className="text-sm text-[var(--color-text-secondary)]">
              {user.email}
            </span>
            <Button variant="secondary" onClick={logout}>
              Sign Out
            </Button>
          </>
        )}
      </div>
```

- [ ] **Step 3: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/app/auth-wrapper.tsx frontend/src/components/layout/nav.tsx && git commit -m "feat(frontend): public route bypass for demo/pricing, add Pricing nav link"
```

---

### Task 3: Demo dropzone + results pages

**Files:**
- Create: `frontend/src/app/demo/page.tsx`
- Create: `frontend/src/app/demo/[id]/page.tsx`

- [ ] **Step 1: Create demo dropzone page**

Create `frontend/src/app/demo/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

export default function DemoPage() {
  const router = useRouter();
  const [paths, setPaths] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const filePaths = paths
      .split("\n")
      .map((p) => p.trim())
      .filter(Boolean);

    if (filePaths.length < 5) {
      setError("At least 5 photos required");
      return;
    }
    if (filePaths.length > 50) {
      setError("Maximum 50 photos allowed");
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.demoUpload({ file_paths: filePaths });
      router.push(`/demo/${res.demo_id}`);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl w-full text-center"
        >
          <h1
            className="text-4xl font-bold text-[var(--color-text)] mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            See AI Results in Minutes
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-8">
            Paste your listing photo S3 paths below. Our AI will curate, score,
            and package them — no account needed.
          </p>

          <GlassCard tilt={false} className="text-left">
            <form onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-2">
                Photo paths (one per line, 5–50 photos)
              </label>
              <textarea
                value={paths}
                onChange={(e) => setPaths(e.target.value)}
                rows={8}
                placeholder={`listings/demo/exterior.jpg\nlistings/demo/living_room.jpg\nlistings/demo/kitchen.jpg\nlistings/demo/bedroom.jpg\nlistings/demo/bathroom.jpg`}
                className="w-full rounded-lg border border-white/30 bg-white/50 backdrop-blur px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-none"
              />
              {error && (
                <p className="text-red-500 text-sm mt-2">{error}</p>
              )}
              <div className="mt-4 flex justify-end">
                <Button type="submit" loading={loading}>
                  Process Photos
                </Button>
              </div>
            </form>
          </GlassCard>
        </motion.div>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Create demo results page**

Create `frontend/src/app/demo/[id]/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";
import type { DemoViewResponse } from "@/lib/types";

export default function DemoResultsPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [demo, setDemo] = useState<DemoViewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);

  useEffect(() => {
    apiClient
      .demoView(id)
      .then(setDemo)
      .catch(() => setDemo(null))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleClaim() {
    setClaiming(true);
    try {
      await apiClient.demoClaim(id);
      router.push("/register?claim=" + id);
    } catch {
      router.push("/register?claim=" + id);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!demo) {
    return (
      <>
        <Nav />
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-[var(--color-text-secondary)]">Demo not found or expired.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <div className="mb-6 text-center">
          <h1
            className="text-3xl font-bold text-[var(--color-text)] mb-2"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Your AI-Curated Package
          </h1>
          <Badge state={demo.state} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 mb-8">
          {demo.photos.map((photo, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
            >
              <GlassCard tilt className="p-3">
                <div className="aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 rounded-lg mb-2 flex items-center justify-center">
                  <span className="text-xs text-slate-400 font-mono truncate px-2">
                    {photo.file_path.split("/").pop()}
                  </span>
                </div>
                {photo.room_label && (
                  <p className="text-xs font-medium text-[var(--color-text)] capitalize">
                    {photo.room_label.replace(/_/g, " ")}
                  </p>
                )}
                {photo.quality_score != null && (
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Score: {photo.quality_score}
                  </p>
                )}
              </GlassCard>
            </motion.div>
          ))}
        </div>

        <div className="text-center">
          <GlassCard tilt={false} className="inline-block max-w-md">
            <h3
              className="text-lg font-semibold mb-2"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Ready to launch this listing?
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              Create an account to claim these results, get branded content,
              social posts, MLS bundles, and AI video tours.
            </p>
            <Button onClick={handleClaim} loading={claiming}>
              Claim &amp; Register
            </Button>
          </GlassCard>
        </div>
      </main>
    </>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/app/demo/ && git commit -m "feat(frontend): add demo dropzone and results pages"
```

---

### Task 4: Pricing page

**Files:**
- Create: `frontend/src/app/pricing/page.tsx`

- [ ] **Step 1: Create pricing page**

Create `frontend/src/app/pricing/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";

const TIERS = [
  {
    name: "Starter",
    price: 29,
    recommended: false,
    features: {
      "Listings / month": "5",
      "Photos / listing": "25",
      "AI Vision (Tier 2)": false,
      "Social Content": false,
      "AI Video Tours": false,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
  {
    name: "Pro",
    price: 99,
    recommended: true,
    features: {
      "Listings / month": "50",
      "Photos / listing": "50",
      "AI Vision (Tier 2)": true,
      "Social Content": true,
      "AI Video Tours": true,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
  {
    name: "Enterprise",
    price: 299,
    recommended: false,
    features: {
      "Listings / month": "500",
      "Photos / listing": "100",
      "AI Vision (Tier 2)": true,
      "Social Content": true,
      "AI Video Tours": true,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
];

export default function PricingPage() {
  return (
    <>
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-16">
        <div className="text-center mb-12">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-bold text-[var(--color-text)] mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Listing Media OS
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg text-[var(--color-text-secondary)]"
          >
            From raw listing media to launch-ready marketing in minutes.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard
                tilt
                className={`relative ${
                  tier.recommended
                    ? "border-[var(--color-cta)] border-2 shadow-[0_0_30px_rgba(249,115,22,0.15)]"
                    : ""
                }`}
              >
                {tier.recommended && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--color-cta)] text-white text-xs font-bold px-3 py-1 rounded-full">
                    Recommended
                  </span>
                )}
                <h2
                  className="text-xl font-bold text-[var(--color-text)] mb-1"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {tier.name}
                </h2>
                <div className="mb-6">
                  <span className="text-3xl font-bold text-[var(--color-text)]">
                    ${tier.price}
                  </span>
                  <span className="text-sm text-[var(--color-text-secondary)]">/mo</span>
                </div>

                <ul className="space-y-3 mb-6">
                  {Object.entries(tier.features).map(([feature, value]) => (
                    <li key={feature} className="flex items-center justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">{feature}</span>
                      {typeof value === "boolean" ? (
                        value ? (
                          <span className="text-green-500 font-bold">&#10003;</span>
                        ) : (
                          <span className="text-slate-300">&#x2014;</span>
                        )
                      ) : (
                        <span className="font-medium text-[var(--color-text)]">{value}</span>
                      )}
                    </li>
                  ))}
                </ul>

                <Link href={`/register?plan=${tier.name.toLowerCase()}`}>
                  <Button
                    className="w-full"
                    variant={tier.recommended ? "primary" : "secondary"}
                  >
                    Get Started
                  </Button>
                </Link>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/app/pricing/ && git commit -m "feat(frontend): add pricing page with three-tier comparison"
```

---

### Task 5: Video player + video upload + social preview components

**Files:**
- Create: `frontend/src/components/listings/video-player.tsx`
- Create: `frontend/src/components/listings/video-upload.tsx`
- Create: `frontend/src/components/listings/social-preview.tsx`

- [ ] **Step 1: Create video player component**

Create `frontend/src/components/listings/video-player.tsx`:

```tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import apiClient from "@/lib/api-client";
import type { VideoResponse, Chapter } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  ai_generated: "AI Generated",
  professional: "Professional",
  user_raw: "User Upload",
};

interface VideoPlayerProps {
  listingId: string;
  onNoVideo?: () => void;
}

export function VideoPlayer({ listingId, onNoVideo }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [video, setVideo] = useState<VideoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getVideo(listingId)
      .then(setVideo)
      .catch(() => {
        setVideo(null);
        onNoVideo?.();
      })
      .finally(() => setLoading(false));
  }, [listingId, onNoVideo]);

  function seekTo(time: number) {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  }

  if (loading) return null;
  if (!video) return null;

  return (
    <GlassCard tilt={false}>
      <div className="flex items-center justify-between mb-3">
        <h3
          className="text-lg font-semibold"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Property Video
        </h3>
        <span className="text-xs font-medium px-2 py-1 rounded-full bg-blue-100 text-blue-700">
          {TYPE_LABELS[video.video_type] || video.video_type}
        </span>
      </div>

      <video
        ref={videoRef}
        src={video.s3_key}
        controls
        poster={video.thumbnail_s3_key || undefined}
        className="w-full rounded-lg bg-black"
      />

      {video.duration_seconds && (
        <p className="text-xs text-[var(--color-text-secondary)] mt-2">
          {video.duration_seconds}s
          {video.clip_count && ` · ${video.clip_count} clips`}
        </p>
      )}

      {video.chapters && video.chapters.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-[var(--color-text)] mb-2">Chapters</p>
          <div className="flex flex-wrap gap-1.5">
            {video.chapters.map((ch: Chapter, i: number) => (
              <motion.button
                key={i}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => seekTo(ch.time)}
                className="text-xs px-2.5 py-1 rounded-full bg-white/60 border border-white/30 hover:bg-white/80 transition-colors cursor-pointer"
                title={ch.description}
              >
                <span className="text-[var(--color-text-secondary)]">
                  {Math.floor(ch.time / 60)}:{String(ch.time % 60).padStart(2, "0")}
                </span>{" "}
                <span className="capitalize">{ch.label.replace(/_/g, " ")}</span>
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  );
}
```

- [ ] **Step 2: Create video upload component**

Create `frontend/src/components/listings/video-upload.tsx`:

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

interface VideoUploadProps {
  listingId: string;
  onUploaded: () => void;
}

export function VideoUpload({ listingId, onUploaded }: VideoUploadProps) {
  const [s3Key, setS3Key] = useState(`videos/${listingId}/`);
  const [videoType, setVideoType] = useState<"professional" | "user_raw">("professional");
  const [duration, setDuration] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!s3Key.startsWith(`videos/${listingId}/`)) {
      setError(`S3 key must start with videos/${listingId}/`);
      return;
    }

    setLoading(true);
    try {
      await apiClient.uploadVideo(listingId, {
        s3_key: s3Key,
        video_type: videoType,
        duration_seconds: duration ? parseInt(duration, 10) : undefined,
      });
      onUploaded();
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <GlassCard tilt={false}>
      <h3
        className="text-lg font-semibold mb-3"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Add Video
      </h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            S3 Key
          </label>
          <input
            type="text"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
            className="w-full rounded-lg border border-white/30 bg-white/50 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            Video Type
          </label>
          <div className="flex gap-4">
            {(["professional", "user_raw"] as const).map((t) => (
              <label key={t} className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="videoType"
                  checked={videoType === t}
                  onChange={() => setVideoType(t)}
                  className="accent-[var(--color-primary)]"
                />
                <span className="capitalize">{t.replace(/_/g, " ")}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            Duration (seconds, optional)
          </label>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="60"
            className="w-32 rounded-lg border border-white/30 bg-white/50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex justify-end">
          <Button type="submit" loading={loading}>
            Register Video
          </Button>
        </div>
      </form>
    </GlassCard>
  );
}
```

- [ ] **Step 3: Create social preview component**

Create `frontend/src/components/listings/social-preview.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import apiClient from "@/lib/api-client";
import type { SocialCut } from "@/lib/types";

const PLATFORM_META: Record<string, { icon: string; label: string; color: string }> = {
  instagram: { icon: "IG", label: "Instagram Reel", color: "bg-pink-100 text-pink-700" },
  tiktok: { icon: "TT", label: "TikTok", color: "bg-slate-100 text-slate-700" },
  facebook: { icon: "FB", label: "Facebook Video", color: "bg-blue-100 text-blue-700" },
  youtube_short: { icon: "YT", label: "YouTube Short", color: "bg-red-100 text-red-700" },
};

interface SocialPreviewProps {
  listingId: string;
}

export function SocialPreview({ listingId }: SocialPreviewProps) {
  const [cuts, setCuts] = useState<SocialCut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getSocialCuts(listingId)
      .then(setCuts)
      .catch(() => setCuts([]))
      .finally(() => setLoading(false));
  }, [listingId]);

  if (loading) return null;
  if (cuts.length === 0) return null;

  return (
    <GlassCard tilt={false}>
      <h3
        className="text-lg font-semibold mb-3"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Social Cuts
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {cuts.map((cut, i) => {
          const meta = PLATFORM_META[cut.platform] || {
            icon: "?",
            label: cut.platform,
            color: "bg-slate-100 text-slate-700",
          };
          return (
            <motion.div
              key={cut.platform}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-lg border border-white/30 bg-white/40 p-3"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${meta.color}`}>
                  {meta.icon}
                </span>
                <span className="text-sm font-medium text-[var(--color-text)]">
                  {meta.label}
                </span>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] space-y-0.5">
                <p>{cut.width}×{cut.height}</p>
                <p>Max {cut.max_duration}s</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </GlassCard>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/components/listings/video-player.tsx frontend/src/components/listings/video-upload.tsx frontend/src/components/listings/social-preview.tsx && git commit -m "feat(frontend): add VideoPlayer, VideoUpload, SocialPreview components"
```

---

### Task 6: Export page + integrate video/social into listing detail

**Files:**
- Create: `frontend/src/app/listings/[id]/export/page.tsx`
- Modify: `frontend/src/app/listings/[id]/page.tsx`

- [ ] **Step 1: Create export download page**

Create `frontend/src/app/listings/[id]/export/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

type Mode = "mls" | "marketing";

const MODE_INFO: Record<Mode, { title: string; items: string[] }> = {
  mls: {
    title: "MLS Package",
    items: [
      "Unbranded photos (MLS-compliant)",
      "MLS-safe description",
      "Standard resolution",
    ],
  },
  marketing: {
    title: "Marketing Package",
    items: [
      "Branded photos with watermark",
      "Marketing description (dual-tone)",
      "Branded flyer PDF",
      "Social media posts",
      "High resolution",
    ],
  },
};

function ExportPage() {
  const params = useParams();
  const id = params.id as string;
  const [mode, setMode] = useState<Mode>("marketing");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setError("");
    setDownloading(true);
    try {
      const res = await apiClient.getExport(id, mode);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      setError(err.message || "Export not available yet");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-8">
        <Link
          href={`/listings/${id}`}
          className="text-sm text-[var(--color-primary)] hover:underline mb-4 inline-block"
        >
          &larr; Back to Listing
        </Link>

        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-6"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Export Package
        </h1>

        {/* Toggle */}
        <div className="flex rounded-xl bg-white/50 backdrop-blur border border-white/30 p-1 mb-6">
          {(["mls", "marketing"] as const).map((m) => (
            <motion.button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                mode === m
                  ? "bg-[var(--color-primary)] text-white shadow-md"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
              whileTap={{ scale: 0.98 }}
            >
              {m === "mls" ? "MLS" : "Marketing"}
            </motion.button>
          ))}
        </div>

        {/* Bundle contents */}
        <GlassCard tilt={false} className="mb-6">
          <h3
            className="text-lg font-semibold mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            {MODE_INFO[mode].title}
          </h3>
          <ul className="space-y-2">
            {MODE_INFO[mode].items.map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-[var(--color-text)]">
                <span className="text-green-500">&#10003;</span>
                {item}
              </li>
            ))}
          </ul>
        </GlassCard>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        <Button onClick={handleDownload} loading={downloading} className="w-full">
          Download {mode === "mls" ? "MLS" : "Marketing"} Package
        </Button>
      </main>
    </>
  );
}

export default function ExportPageWrapper() {
  return (
    <ProtectedRoute>
      <ExportPage />
    </ProtectedRoute>
  );
}
```

- [ ] **Step 2: Integrate video + social into listing detail page**

In `frontend/src/app/listings/[id]/page.tsx`, add these imports after the existing imports:

```typescript
import { VideoPlayer } from "@/components/listings/video-player";
import { VideoUpload } from "@/components/listings/video-upload";
import { SocialPreview } from "@/components/listings/social-preview";
```

Add a state variable for showing video upload in the `ListingDetail` function:

```typescript
  const [showVideoUpload, setShowVideoUpload] = useState(false);
```

Add a `Link` import if not already present (it is). Add an export page link inside the Actions GlassCard, after the existing export buttons:

```tsx
                {["approved", "exporting", "delivered"].includes(listing.state) && (
                  <>
                    <Link href={`/listings/${id}/export`}>
                      <Button variant="secondary">Export Packages</Button>
                    </Link>
                    <Button onClick={() => handleExport("marketing")}>
                      Quick Download Marketing
                    </Button>
                  </>
                )}
```

Add a new section after the two-column grid `</div>` closing tag (before `</main>`):

```tsx
        {/* Video + Social Section */}
        {["approved", "exporting", "delivered"].includes(listing.state) && (
          <div className="mt-8 space-y-6">
            <VideoPlayer
              listingId={id}
              onNoVideo={() => setShowVideoUpload(true)}
            />
            {showVideoUpload && (
              <VideoUpload
                listingId={id}
                onUploaded={() => {
                  setShowVideoUpload(false);
                  fetchData();
                }}
              />
            )}
            <SocialPreview listingId={id} />
          </div>
        )}
```

- [ ] **Step 3: Verify build**

```bash
cd /c/Users/Jeff/launchlens/frontend && npx next build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add frontend/src/app/listings/\[id\]/export/ frontend/src/app/listings/\[id\]/page.tsx && git commit -m "feat(frontend): add export page, integrate video + social into listing detail"
```

---

## NOT in scope

- Actual file upload (drag-and-drop → S3) — Phase 2, MVP uses S3 key strings
- HLS/DASH streaming — MVP uses native `<video>` with S3 URLs
- Video analytics (views, watch time)
- Real social post rendering (just metadata cards)
- Demo rate limiting UI (backend returns error, frontend shows it)
- Responsive mobile optimization (desktop-first MVP)
