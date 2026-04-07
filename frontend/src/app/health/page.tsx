"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api-client";
import type { HealthSummaryResponse } from "@/lib/types";
import { HealthBadge } from "@/components/listings/health-badge";

export default function HealthDashboardPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<HealthSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getHealthSummary()
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Listing Health</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-100 p-6 animate-pulse">
              <div className="h-8 bg-slate-100 rounded w-1/2 mb-2" />
              <div className="h-12 bg-slate-50 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!summary || summary.total_scored === 0) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Listing Health</h1>
        <div className="bg-white rounded-xl border border-slate-100 p-12 text-center">
          <p className="text-slate-500">No health scores yet. Scores are calculated after listings are delivered.</p>
        </div>
      </div>
    );
  }

  const { distribution, average_score, total_scored, top_listings, bottom_listings } = summary;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Listing Health</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-100 p-5">
          <p className="text-sm text-slate-500 mb-1">Average Score</p>
          <p className="text-3xl font-bold text-slate-900">{Math.round(average_score)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-5">
          <p className="text-sm text-slate-500 mb-1">Healthy</p>
          <p className="text-3xl font-bold text-emerald-600">{distribution.green}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-5">
          <p className="text-sm text-slate-500 mb-1">Needs Attention</p>
          <p className="text-3xl font-bold text-amber-600">{distribution.yellow}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-5">
          <p className="text-sm text-slate-500 mb-1">At Risk</p>
          <p className="text-3xl font-bold text-red-600">{distribution.red}</p>
        </div>
      </div>

      {/* Distribution Bar */}
      <div className="bg-white rounded-xl border border-slate-100 p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-3">Score Distribution</h2>
        <div className="flex h-6 rounded-full overflow-hidden bg-slate-100">
          {total_scored > 0 && (
            <>
              <div
                className="bg-emerald-500 transition-all"
                style={{ width: `${(distribution.green / total_scored) * 100}%` }}
                title={`${distribution.green} healthy`}
              />
              <div
                className="bg-amber-500 transition-all"
                style={{ width: `${(distribution.yellow / total_scored) * 100}%` }}
                title={`${distribution.yellow} needs attention`}
              />
              <div
                className="bg-red-500 transition-all"
                style={{ width: `${(distribution.red / total_scored) * 100}%` }}
                title={`${distribution.red} at risk`}
              />
            </>
          )}
        </div>
        <p className="text-xs text-slate-400 mt-2">{total_scored} listings scored</p>
      </div>

      {/* Top & Bottom Listings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-100 p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-3">Top Performers</h2>
          <div className="space-y-2">
            {top_listings.map((l) => (
              <div
                key={l.listing_id}
                onClick={() => router.push(`/listings/${l.listing_id}`)}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                <span className="text-sm text-slate-700 truncate">{l.address.street || l.listing_id}</span>
                <HealthBadge score={l.overall_score} />
              </div>
            ))}
            {top_listings.length === 0 && <p className="text-sm text-slate-400">No data yet</p>}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-100 p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-3">Needs Improvement</h2>
          <div className="space-y-2">
            {bottom_listings.map((l) => (
              <div
                key={l.listing_id}
                onClick={() => router.push(`/listings/${l.listing_id}`)}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                <span className="text-sm text-slate-700 truncate">{l.address.street || l.listing_id}</span>
                <HealthBadge score={l.overall_score} />
              </div>
            ))}
            {bottom_listings.length === 0 && <p className="text-sm text-slate-400">No data yet</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
