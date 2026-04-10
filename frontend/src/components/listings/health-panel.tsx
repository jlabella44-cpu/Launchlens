"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
import type { ListingHealthResponse, HealthSubScoreDetail } from "@/lib/types";
import { HealthBadge } from "./health-badge";

interface HealthPanelProps {
  listingId: string;
}

const SUB_SCORE_LABELS: Record<string, { label: string; description: string }> = {
  media_quality: { label: "Media Quality", description: "Photo quality, coverage, and hero strength" },
  content_readiness: { label: "Content Readiness", description: "Descriptions, flyers, social posts, and exports" },
  pipeline_velocity: { label: "Pipeline Speed", description: "Processing time, review speed, and reliability" },
  syndication: { label: "Syndication", description: "IDX feed presence and photo match" },
  market_signal: { label: "Market Signal", description: "DOM, price stability, and status progression" },
};

function ScoreBar({ label, detail, description }: { label: string; detail: HealthSubScoreDetail; description: string }) {
  const pct = Math.min(100, Math.max(0, detail.score));
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <div>
          <span className="text-sm font-medium text-[var(--color-text)]">{label}</span>
          <span className="text-xs text-[var(--color-text-secondary)] ml-2">({Math.round(detail.weight * 100)}%)</span>
        </div>
        <span className="text-sm font-semibold text-[var(--color-text)]">{detail.score}</span>
      </div>
      <div className="h-2 bg-[var(--color-background)] rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-[var(--color-text-secondary)]">{description}</p>
    </div>
  );
}

export function HealthPanel({ listingId }: HealthPanelProps) {
  const [health, setHealth] = useState<ListingHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .getListingHealth(listingId)
      .then(setHealth)
      .catch(() => setError("Unable to load health score"))
      .finally(() => setLoading(false));
  }, [listingId]);

  if (loading) {
    return (
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-card-border)] p-6 animate-pulse">
        <div className="h-6 bg-[var(--color-background)] rounded w-1/3 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-[var(--color-background)] rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !health) {
    return null; // Silently hide if health data unavailable
  }

  const breakdown = health.breakdown;
  const entries = Object.entries(breakdown).filter(
    ([, v]) => v !== undefined && v !== null,
  ) as [string, HealthSubScoreDetail][];

  return (
    <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-card-border)] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--color-text)]">Listing Health</h3>
        <HealthBadge score={health.overall_score} size="md" />
      </div>

      <div className="space-y-3">
        {entries.map(([key, detail]) => {
          const meta = SUB_SCORE_LABELS[key] || { label: key, description: "" };
          return <ScoreBar key={key} label={meta.label} detail={detail} description={meta.description} />;
        })}
      </div>

      {health.trend.length > 1 && (
        <div className="pt-3 border-t border-[var(--color-card-border)]">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {health.trend.length}-day trend: {health.trend[0].overall} → {health.trend[health.trend.length - 1].overall}
          </p>
        </div>
      )}

      {health.calculated_at && (
        <p className="text-xs text-[var(--color-text-secondary)]">
          Last updated: {new Date(health.calculated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
