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
