"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import apiClient from "@/lib/api-client";
import type { PerformanceInsightsResponse, OutcomeSummaryResponse } from "@/lib/types";

const GRADE_COLORS: Record<string, string> = {
  A: "text-emerald-600 bg-emerald-50",
  B: "text-blue-600 bg-blue-50",
  C: "text-amber-600 bg-amber-50",
  D: "text-orange-600 bg-orange-50",
  F: "text-red-600 bg-red-50",
};

function GradeBadge({ grade }: { grade: string }) {
  const cls = GRADE_COLORS[grade] || "text-gray-600 bg-gray-50";
  return (
    <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${cls}`}>
      {grade}
    </span>
  );
}

function BoostBar({ boost, label }: { boost: number; label: string }) {
  const pct = Math.min(Math.max((boost - 0.5) / 1.0 * 100, 0), 100);
  const isPositive = boost >= 1.0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-[var(--color-text-secondary)] w-24 truncate">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isPositive ? "bg-emerald-500" : "bg-orange-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-medium w-12 text-right ${isPositive ? "text-emerald-600" : "text-orange-600"}`}>
        {boost >= 1.0 ? "+" : ""}{((boost - 1.0) * 100).toFixed(0)}%
      </span>
    </div>
  );
}

export function PerformanceIntelligence() {
  const [insights, setInsights] = useState<PerformanceInsightsResponse | null>(null);
  const [outcomes, setOutcomes] = useState<OutcomeSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const [insRes, outRes] = await Promise.allSettled([
        apiClient.getPerformanceInsights(),
        apiClient.getOutcomeSummary(),
      ]);
      if (insRes.status === "fulfilled") setInsights(insRes.value);
      if (outRes.status === "fulfilled") setOutcomes(outRes.value);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-48 rounded-xl bg-white/50 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!insights || insights.outcomes_count === 0) {
    return (
      <GlassCard tilt={false}>
        <div className="text-center py-12">
          <div className="text-4xl mb-3">&#128202;</div>
          <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">
            No Outcome Data Yet
          </h3>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto">
            Performance insights appear as your listings sell. Connect an IDX feed
            in Settings to track listing outcomes automatically.
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <GlassCard tilt={false}>
          <p className="text-sm text-[var(--color-text-secondary)]">{insights.summary}</p>
        </GlassCard>
      </motion.div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Tracked", value: outcomes?.total_tracked ?? 0 },
          { label: "Closed", value: outcomes?.total_closed ?? 0 },
          {
            label: "Avg DOM",
            value: insights.avg_dom != null ? `${insights.avg_dom}d` : "N/A",
          },
          {
            label: "Sale/List",
            value: insights.avg_price_ratio != null
              ? `${(insights.avg_price_ratio * 100).toFixed(1)}%`
              : "N/A",
          },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.06 * i }}
          >
            <GlassCard tilt={false} className="text-center">
              <p className="text-2xl font-bold text-[var(--color-primary)]">{stat.value}</p>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">{stat.label}</p>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* Grade Distribution */}
      {Object.keys(insights.grade_distribution).length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <GlassCard tilt={false}>
            <h3 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
              Outcome Grades
            </h3>
            <div className="flex gap-4 flex-wrap">
              {["A", "B", "C", "D", "F"].map((g) => {
                const count = insights.grade_distribution[g] || 0;
                if (count === 0) return null;
                return (
                  <div key={g} className="flex items-center gap-2">
                    <GradeBadge grade={g} />
                    <span className="text-sm text-[var(--color-text-secondary)]">
                      {count} listing{count !== 1 ? "s" : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Room Performance */}
        {insights.top_rooms.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <GlassCard tilt={false}>
              <h3 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
                Room Performance
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] mb-4">
                How each room type in your photo packages correlates with sale outcomes.
              </p>
              <div className="space-y-3">
                {insights.top_rooms.map((r) => (
                  <BoostBar key={r.room} boost={r.boost} label={r.room.replace(/_/g, " ")} />
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Hero Photo Insights */}
        {insights.hero_insights.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <GlassCard tilt={false}>
              <h3 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
                Hero Photo Impact
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] mb-4">
                Which room as the lead photo correlates with faster sales.
              </p>
              <div className="space-y-3">
                {insights.hero_insights.map((h) => (
                  <div key={h.room} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                    <span className="text-sm font-medium text-[var(--color-text)] capitalize">
                      {h.room.replace(/_/g, " ")}
                    </span>
                    <div className="flex items-center gap-3">
                      {h.avg_dom != null && (
                        <span className="text-xs text-[var(--color-text-secondary)]">
                          {h.avg_dom}d avg
                        </span>
                      )}
                      <span className={`text-xs font-bold ${h.boost >= 1.0 ? "text-emerald-600" : "text-orange-600"}`}>
                        {h.boost >= 1.0 ? "+" : ""}{((h.boost - 1.0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </div>

      {/* Photo Quality Impact */}
      {insights.quality_impact.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <GlassCard tilt={false}>
            <h3 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
              Photo Quality vs. Outcomes
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              How photo quality scores correlate with listing performance.
            </p>
            <div className="space-y-3">
              {insights.quality_impact.map((q) => (
                <BoostBar key={q.bucket} boost={q.boost} label={q.bucket} />
              ))}
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Recent Outcomes Table */}
      {outcomes && outcomes.listings.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
          <GlassCard tilt={false}>
            <h3 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
              Recent Outcomes
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[var(--color-text-secondary)] border-b border-white/10">
                    <th className="text-left py-2 px-2">Status</th>
                    <th className="text-left py-2 px-2">Grade</th>
                    <th className="text-right py-2 px-2">DOM</th>
                    <th className="text-right py-2 px-2">Sale/List</th>
                    <th className="text-right py-2 px-2">Photos</th>
                    <th className="text-left py-2 px-2">Hero</th>
                  </tr>
                </thead>
                <tbody>
                  {outcomes.listings.slice(0, 10).map((o) => (
                    <tr key={o.listing_id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2 capitalize">{o.status}</td>
                      <td className="py-2 px-2">
                        {o.outcome_grade ? <GradeBadge grade={o.outcome_grade} /> : "-"}
                      </td>
                      <td className="py-2 px-2 text-right">{o.days_on_market ?? "-"}</td>
                      <td className="py-2 px-2 text-right">
                        {o.price_ratio != null ? `${(o.price_ratio * 100).toFixed(1)}%` : "-"}
                      </td>
                      <td className="py-2 px-2 text-right">{o.total_photos_mls ?? "-"}</td>
                      <td className="py-2 px-2 capitalize">{o.hero_room_label?.replace(/_/g, " ") ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </motion.div>
      )}
    </div>
  );
}
