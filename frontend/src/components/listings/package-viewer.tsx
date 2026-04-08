"use client";

import Image from "next/image";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import type { PackageSelection } from "@/lib/types";

interface PackageViewerProps {
  selections: PackageSelection[];
}

export function PackageViewer({ selections }: PackageViewerProps) {
  if (selections.length === 0) {
    return (
      <GlassCard tilt={false}>
        <p className="text-[var(--color-text-secondary)] text-center py-4">
          No package selections yet. Upload assets and wait for the AI pipeline to curate.
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard tilt={false}>
      <h3
        className="text-lg font-semibold mb-4"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Curated Package ({selections.length} photos)
      </h3>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {selections.map((sel) => (
          <div
            key={`${sel.asset_id}-${sel.position}`}
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/50"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-mono text-[var(--color-text-secondary)] w-6">
                #{sel.position + 1}
              </span>
              {sel.thumbnail_url ? (
                <Image
                  src={sel.thumbnail_url}
                  alt={`Photo ${sel.position + 1}`}
                  width={48}
                  height={36}
                  className="object-cover rounded"
                />
              ) : (
                <div className="w-12 h-9 rounded bg-slate-100 flex items-center justify-center">
                  <span className="text-[10px] text-slate-400">{sel.asset_id.slice(0, 6)}</span>
                </div>
              )}
              {sel.position === 0 && (
                <span className="text-xs font-bold text-[var(--color-cta)] bg-orange-50 px-2 py-0.5 rounded-full">
                  HERO
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--color-text-secondary)]">
                {Math.round(sel.composite_score)}pts
              </span>
              <span className="text-xs text-[var(--color-text-secondary)]">
                {sel.selected_by}
              </span>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
