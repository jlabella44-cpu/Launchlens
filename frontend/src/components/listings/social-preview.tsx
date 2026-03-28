"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { PlanBadge } from "@/components/ui/plan-badge";
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
        className="text-lg font-semibold mb-3 flex items-center gap-2"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Social Cuts
        <PlanBadge feature="social_content" />
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
