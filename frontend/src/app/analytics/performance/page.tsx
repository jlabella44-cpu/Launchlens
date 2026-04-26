"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";

interface Insight {
  type: string;
  data: Record<string, unknown>;
  sample_size: number;
}

interface PerformanceOverview {
  tenant_id: string;
  total_outcomes: number;
  insights: Insight[];
  sufficient_data: boolean;
}

const INSIGHT_LABELS: Record<string, { title: string; icon: string }> = {
  dom_summary: { title: "Days on Market", icon: "clock" },
  quality_dom_correlation: { title: "Photo Quality Impact", icon: "camera" },
  hero_impact: { title: "Hero Photo Impact", icon: "star" },
  coverage_impact: { title: "Coverage Completeness", icon: "grid" },
  override_impact: { title: "AI Trust Factor", icon: "cpu" },
};

function InsightCard({ insight }: { insight: Insight }) {
  const meta = INSIGHT_LABELS[insight.type] || { title: insight.type, icon: "chart" };
  const d = insight.data as Record<string, number>;

  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{meta.title}</h3>
        <span className="text-[10px] text-slate-400">n={insight.sample_size}</span>
      </div>

      {insight.type === "dom_summary" && (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-2xl font-bold text-slate-900">{d.avg_dom}</p>
            <p className="text-[10px] text-slate-400 uppercase">Avg DOM</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-emerald-600">{d.min_dom}</p>
            <p className="text-[10px] text-slate-400 uppercase">Fastest</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-400">{d.sold_count}/{d.total}</p>
            <p className="text-[10px] text-slate-400 uppercase">Sold</p>
          </div>
        </div>
      )}

      {insight.type === "quality_dom_correlation" && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">High quality photos (&ge;75)</span>
            <span className="text-sm font-semibold text-emerald-600">{d.high_quality_avg_dom} days</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Lower quality photos (&lt;75)</span>
            <span className="text-sm font-semibold text-red-500">{d.low_quality_avg_dom} days</span>
          </div>
          {d.difference_days > 0 && (
            <p className="text-xs text-emerald-600 font-medium bg-emerald-50 rounded-lg px-3 py-1.5">
              Higher quality photos sell {d.difference_days} days faster ({d.difference_pct}%)
            </p>
          )}
        </div>
      )}

      {insight.type === "hero_impact" && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Strong hero (&ge;80)</span>
            <span className="text-sm font-semibold text-emerald-600">{d.strong_hero_avg_dom} days</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Weak hero (&lt;80)</span>
            <span className="text-sm font-semibold text-amber-600">{d.weak_hero_avg_dom} days</span>
          </div>
        </div>
      )}

      {insight.type === "coverage_impact" && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Full coverage (all rooms)</span>
            <span className="text-sm font-semibold text-emerald-600">{d.full_coverage_avg_dom} days</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Partial coverage</span>
            <span className="text-sm font-semibold text-amber-600">{d.partial_coverage_avg_dom} days</span>
          </div>
        </div>
      )}

      {insight.type === "override_impact" && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Trusted AI selections (&le;10%)</span>
            <span className="text-sm font-semibold text-emerald-600">{d.trusted_ai_avg_dom} days</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">High override rate (&gt;10%)</span>
            <span className="text-sm font-semibold text-amber-600">{d.high_override_avg_dom} days</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PerformanceIntelligencePage() {
  const [data, setData] = useState<PerformanceOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getPerformanceOverview()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Performance Intelligence</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-100 p-6 animate-pulse">
              <div className="h-4 bg-slate-100 rounded w-1/3 mb-4" />
              <div className="h-16 bg-slate-50 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Performance Intelligence</h1>
        <p className="text-sm text-slate-500 mt-1">
          How your photo selections correlate with listing outcomes
        </p>
      </div>

      {!data?.sufficient_data ? (
        <div className="bg-white rounded-xl border border-slate-100 p-12 text-center">
          <p className="text-slate-500 mb-2">Not enough data yet</p>
          <p className="text-sm text-slate-400">
            Performance insights require at least {5} delivered listings with IDX outcome data.
            You have {data?.total_outcomes || 0} so far.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-sm text-slate-600">
              Analyzing <strong>{data.total_outcomes}</strong> delivered listings with outcome data
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.insights.map((insight, i) => (
              <InsightCard key={`${insight.type}-${i}`} insight={insight} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
