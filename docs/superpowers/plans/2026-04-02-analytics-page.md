# Analytics Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `/analytics/usage` 404, add a `/analytics/usage` backend endpoint, and build a frontend analytics page with charts showing pipeline performance, listing timeline, credit usage, and state breakdown.

**Architecture:** Add a `/analytics/usage` endpoint to the existing analytics router (fixing the path mismatch where frontend calls `/analytics/usage` but the data lives at `/settings/usage`). Install recharts for charting. Build a new `/analytics` route in the frontend with four visualization sections: stat cards, listing timeline chart, pipeline state breakdown, and credit usage history.

**Tech Stack:** FastAPI (backend), Next.js App Router + recharts + framer-motion (frontend), SQLAlchemy async queries

---

## File Structure

**Backend:**
- Modify: `src/listingjet/api/analytics.py` — add `/usage` and `/credits` endpoints
- No new files needed

**Frontend:**
- Create: `frontend/src/app/analytics/page.tsx` — the analytics page
- Create: `frontend/src/components/analytics/stat-card.tsx` — reusable stat card (extracted from dashboard)
- Create: `frontend/src/components/analytics/timeline-chart.tsx` — recharts line chart for listing timeline
- Create: `frontend/src/components/analytics/state-breakdown.tsx` — recharts bar/pie chart for pipeline states
- Create: `frontend/src/components/analytics/credit-history.tsx` — recharts area chart for credit transactions
- Modify: `frontend/src/lib/api-client.ts` — add analytics API methods
- Modify: `frontend/src/lib/types.ts` — add analytics response types

---

### Task 1: Fix the 404 — Add `/analytics/usage` backend endpoint

**Files:**
- Modify: `src/listingjet/api/analytics.py`

This is the highest-priority fix. The frontend calls `/analytics/usage` but the backend only has `/settings/usage`. We'll add a proper `/analytics/usage` endpoint to the analytics router that returns what the frontend `UsageResponse` type expects: `{listings_this_month, total_assets, total_listings}`.

- [ ] **Step 1: Add the `/usage` endpoint to `analytics.py`**

Add this after the existing imports at the top of the file:

```python
from listingjet.models.asset import Asset
```

Add this endpoint after the `analytics_timeline` function:

```python
@router.get("/usage")
async def analytics_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Usage summary for dashboard: listings this month, total assets, total listings."""
    tid = current_user.tenant_id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_listings = (await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == tid)
    )).scalar() or 0

    listings_this_month = (await db.execute(
        select(func.count(Listing.id)).where(
            Listing.tenant_id == tid,
            Listing.created_at >= month_start,
            Listing.is_demo.is_(False),
        )
    )).scalar() or 0

    total_assets = (await db.execute(
        select(func.count(Asset.id))
        .join(Listing, Asset.listing_id == Listing.id)
        .where(Listing.tenant_id == tid)
    )).scalar() or 0

    return {
        "listings_this_month": listings_this_month,
        "total_assets": total_assets,
        "total_listings": total_listings,
    }
```

- [ ] **Step 2: Verify the Asset model import path**

Run: `grep -r "class Asset" src/listingjet/models/`

Confirm the Asset model exists and has `listing_id` and `id` fields.

- [ ] **Step 3: Run existing analytics tests**

Run: `pytest tests/ -k "analytics" -v --tb=short`

Expected: existing tests still pass (no regressions)

- [ ] **Step 4: Commit**

```bash
git checkout -b feat/analytics-page
git add src/listingjet/api/analytics.py
git commit -m "fix: add /analytics/usage endpoint to resolve frontend 404"
```

---

### Task 2: Add `/analytics/credits` backend endpoint

**Files:**
- Modify: `src/listingjet/api/analytics.py`

Add an endpoint that returns credit transaction history for charting.

- [ ] **Step 1: Add the credits endpoint**

Add this import at the top of `analytics.py`:

```python
from listingjet.models.credit_transaction import CreditTransaction
```

Add this endpoint after the `analytics_usage` function:

```python
@router.get("/credits")
async def analytics_credits(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Credit transaction history for charting."""
    tid = current_user.tenant_id
    start = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(CreditTransaction)
        .where(
            CreditTransaction.tenant_id == tid,
            CreditTransaction.created_at >= start,
        )
        .order_by(CreditTransaction.created_at.asc())
    )).scalars().all()

    return {
        "days": days,
        "data": [
            {
                "date": row.created_at.isoformat(),
                "amount": row.amount,
                "balance_after": row.balance_after,
                "type": row.transaction_type,
                "description": row.description,
            }
            for row in rows
        ],
    }
```

- [ ] **Step 2: Verify the CreditTransaction model**

Run: `grep -r "class CreditTransaction" src/listingjet/models/`

Confirm it has `tenant_id`, `created_at`, `amount`, `balance_after`, `transaction_type`, `description` fields.

- [ ] **Step 3: Commit**

```bash
git add src/listingjet/api/analytics.py
git commit -m "feat: add /analytics/credits endpoint for credit history charting"
```

---

### Task 3: Install recharts and add frontend types

**Files:**
- Modify: `frontend/package.json` (via npm)
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Install recharts**

```bash
cd frontend && npm install recharts
```

- [ ] **Step 2: Add analytics types to `types.ts`**

Add at the end of `frontend/src/lib/types.ts`:

```typescript
export interface AnalyticsOverview {
  total_listings: number;
  delivered: number;
  by_state: Record<string, number>;
  avg_pipeline_minutes: number | null;
  success_rate_pct: number | null;
  events_last_30d: Record<string, number>;
}

export interface TimelineDataPoint {
  date: string;
  count: number;
}

export interface AnalyticsTimeline {
  days: number;
  data: TimelineDataPoint[];
}

export interface CreditDataPoint {
  date: string;
  amount: number;
  balance_after: number;
  type: string;
  description: string | null;
}

export interface AnalyticsCredits {
  days: number;
  data: CreditDataPoint[];
}
```

- [ ] **Step 3: Add API methods to `api-client.ts`**

Add these methods inside the `ApiClient` class, after the existing `getUsage()` method (~line 268):

```typescript
  // Analytics
  async getAnalyticsOverview(): Promise<AnalyticsOverview> {
    return this.request<AnalyticsOverview>("/analytics/overview");
  }

  async getAnalyticsTimeline(days = 30): Promise<AnalyticsTimeline> {
    return this.request<AnalyticsTimeline>(`/analytics/timeline?days=${days}`);
  }

  async getAnalyticsCredits(days = 30): Promise<AnalyticsCredits> {
    return this.request<AnalyticsCredits>(`/analytics/credits?days=${days}`);
  }
```

Update the import in `api-client.ts` to include the new types (add to the existing type import block):

```typescript
import type {
  // ... existing imports ...
  AnalyticsOverview,
  AnalyticsTimeline,
  AnalyticsCredits,
} from "./types";
```

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/lib/types.ts frontend/src/lib/api-client.ts
git commit -m "feat: add recharts, analytics types, and API client methods"
```

---

### Task 4: Build analytics chart components

**Files:**
- Create: `frontend/src/components/analytics/timeline-chart.tsx`
- Create: `frontend/src/components/analytics/state-breakdown.tsx`
- Create: `frontend/src/components/analytics/credit-history.tsx`

- [ ] **Step 1: Create timeline chart component**

Create `frontend/src/components/analytics/timeline-chart.tsx`:

```tsx
"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { TimelineDataPoint } from "@/lib/types";

export function TimelineChart({ data }: { data: TimelineDataPoint[] }) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
        No listing data yet
      </p>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={formatted}>
        <defs>
          <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke="var(--color-primary)"
          strokeWidth={2}
          fill="url(#colorCount)"
          name="Listings"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Create state breakdown component**

Create `frontend/src/components/analytics/state-breakdown.tsx`:

```tsx
"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

const STATE_COLORS: Record<string, string> = {
  new: "#94a3b8",
  uploading: "#60a5fa",
  analyzing: "#a78bfa",
  awaiting_review: "#fbbf24",
  in_review: "#f97316",
  approved: "#34d399",
  delivered: "#10b981",
  failed: "#ef4444",
  cancelled: "#6b7280",
  exporting: "#3b82f6",
  demo: "#d1d5db",
  pipeline_timeout: "#dc2626",
};

const STATE_LABELS: Record<string, string> = {
  new: "New",
  uploading: "Uploading",
  analyzing: "Analyzing",
  awaiting_review: "Awaiting Review",
  in_review: "In Review",
  approved: "Approved",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
  exporting: "Exporting",
  demo: "Demo",
  pipeline_timeout: "Timeout",
};

export function StateBreakdown({ byState }: { byState: Record<string, number> }) {
  const data = Object.entries(byState)
    .filter(([, count]) => count > 0)
    .map(([state, count]) => ({
      state,
      label: STATE_LABELS[state] || state,
      count,
      color: STATE_COLORS[state] || "#94a3b8",
    }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
        No listings yet
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          type="number"
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={100}
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="count" name="Listings" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell key={entry.state} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: Create credit history component**

Create `frontend/src/components/analytics/credit-history.tsx`:

```tsx
"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { CreditDataPoint } from "@/lib/types";

export function CreditHistory({ data }: { data: CreditDataPoint[] }) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
        No credit activity yet
      </p>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value: number, name: string) => {
            if (name === "Balance") return [value, "Credits"];
            const sign = value >= 0 ? "+" : "";
            return [`${sign}${value}`, "Change"];
          }}
        />
        <Line
          type="stepAfter"
          dataKey="balance_after"
          stroke="var(--color-primary)"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Balance"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/analytics/
git commit -m "feat: add analytics chart components (timeline, state breakdown, credit history)"
```

---

### Task 5: Build the analytics page

**Files:**
- Create: `frontend/src/app/analytics/page.tsx`

- [ ] **Step 1: Create the analytics page**

Create `frontend/src/app/analytics/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { TimelineChart } from "@/components/analytics/timeline-chart";
import { StateBreakdown } from "@/components/analytics/state-breakdown";
import { CreditHistory } from "@/components/analytics/credit-history";
import apiClient from "@/lib/api-client";
import type {
  AnalyticsOverview,
  AnalyticsTimeline,
  AnalyticsCredits,
} from "@/lib/types";

function AnalyticsContent() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeline, setTimeline] = useState<AnalyticsTimeline | null>(null);
  const [credits, setCredits] = useState<AnalyticsCredits | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(30);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      const [overviewRes, timelineRes, creditsRes] = await Promise.allSettled([
        apiClient.getAnalyticsOverview(),
        apiClient.getAnalyticsTimeline(timeRange),
        apiClient.getAnalyticsCredits(timeRange),
      ]);

      if (overviewRes.status === "fulfilled") setOverview(overviewRes.value);
      if (timelineRes.status === "fulfilled") setTimeline(timelineRes.value);
      if (creditsRes.status === "fulfilled") setCredits(creditsRes.value);
      setLoading(false);
    }

    fetchAll();
  }, [timeRange]);

  if (loading) {
    return (
      <>
        <Nav />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
          <div className="h-10 w-48 rounded-lg bg-white/50 animate-pulse" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-white/50 animate-pulse" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80 rounded-xl bg-white/50 animate-pulse" />
            <div className="h-80 rounded-xl bg-white/50 animate-pulse" />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Nav />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1
            className="text-2xl sm:text-3xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Analytics
          </h1>
          <div className="flex gap-2">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  timeRange === days
                    ? "bg-[var(--color-primary)] text-white"
                    : "bg-white/10 text-[var(--color-text-secondary)] hover:bg-white/20"
                }`}
              >
                {days}d
              </button>
            ))}
          </div>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Total Listings", value: overview?.total_listings ?? 0 },
            { label: "Delivered", value: overview?.delivered ?? 0 },
            {
              label: "Success Rate",
              value: overview?.success_rate_pct != null
                ? `${overview.success_rate_pct}%`
                : "N/A",
            },
            {
              label: "Avg Pipeline",
              value: overview?.avg_pipeline_minutes != null
                ? `${overview.avg_pipeline_minutes}m`
                : "N/A",
            },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * i }}
            >
              <GlassCard tilt={false} className="text-center">
                <p className="text-2xl sm:text-3xl font-bold text-[var(--color-primary)]">
                  {stat.value}
                </p>
                <p className="text-xs sm:text-sm text-[var(--color-text-secondary)] mt-1">
                  {stat.label}
                </p>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <GlassCard tilt={false}>
              <h2
                className="text-lg font-semibold text-[var(--color-text)] mb-4"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Listings Over Time
              </h2>
              <TimelineChart data={timeline?.data ?? []} />
            </GlassCard>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <GlassCard tilt={false}>
              <h2
                className="text-lg font-semibold text-[var(--color-text)] mb-4"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Pipeline Breakdown
              </h2>
              <StateBreakdown byState={overview?.by_state ?? {}} />
            </GlassCard>
          </motion.div>
        </div>

        {/* Charts Row 2 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <GlassCard tilt={false}>
            <h2
              className="text-lg font-semibold text-[var(--color-text)] mb-4"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Credit Balance History
            </h2>
            <CreditHistory data={credits?.data ?? []} />
          </GlassCard>
        </motion.div>
      </motion.div>
    </>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <AnalyticsContent />
    </ProtectedRoute>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/analytics/page.tsx
git commit -m "feat: add analytics page with charts and time range selector"
```

---

### Task 6: Add analytics link to navigation

**Files:**
- Modify: `frontend/src/components/layout/nav.tsx`

- [ ] **Step 1: Find and read the nav component**

Run: `cat frontend/src/components/layout/nav.tsx`

Look for the navigation links array/list.

- [ ] **Step 2: Add analytics link**

Add an "Analytics" link to the nav alongside the existing links (Dashboard, Listings, etc.). Place it after "Listings" in the nav order. Match the existing link pattern exactly.

- [ ] **Step 3: Verify the dev server compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/nav.tsx
git commit -m "feat: add analytics link to navigation"
```

---

### Task 7: Final verification and PR

- [ ] **Step 1: Run backend tests**

```bash
pytest tests/ -k "analytics" -v --tb=short
```

Expected: all pass

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: clean build, no type errors

- [ ] **Step 3: Push and create PR**

```bash
git push -u origin feat/analytics-page
```

Create PR with title: `feat: analytics page with pipeline, timeline, and credit charts`
