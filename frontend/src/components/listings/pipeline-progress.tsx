"use client";

import { useEffect, useState, useCallback, memo } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import apiClient from "@/lib/api-client";
import type { PipelineStep } from "@/lib/types";

const STATUS_ICON: Record<string, { icon: string; color: string; bg: string }> = {
  completed: { icon: "✓", color: "text-green-600", bg: "bg-green-100" },
  in_progress: { icon: "⟳", color: "text-blue-600", bg: "bg-blue-100" },
  failed: { icon: "✕", color: "text-red-600", bg: "bg-red-100" },
  pending: { icon: "○", color: "text-slate-400", bg: "bg-slate-100" },
  skipped: { icon: "–", color: "text-slate-400", bg: "bg-slate-50" },
};

interface PipelineProgressProps {
  listingId: string;
  listingState: string;
}

// Memoized to prevent unnecessary re-renders from parent polling
function PipelineProgressInner({ listingId, listingState }: PipelineProgressProps) {
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiClient.getPipelineStatus(listingId);
      setSteps(res.steps);
    } catch {
      // Endpoint may not exist yet — silently ignore
    } finally {
      setLoading(false);
    }
  }, [listingId]);

  // Fetch once on mount and when listingState changes (parent handles polling)
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus, listingState]);

  if (loading || steps.length === 0) return null;

  return (
    <GlassCard tilt={false}>
      <h3
        className="text-lg font-semibold mb-4"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Pipeline Progress
      </h3>
      <div className="space-y-1">
        {steps.map((step, i) => {
          const meta = STATUS_ICON[step.status] || STATUS_ICON.pending;
          return (
            <motion.div
              key={step.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className="flex items-center gap-3 py-1.5"
            >
              <span
                className={`w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold ${meta.bg} ${meta.color} ${
                  step.status === "in_progress" ? "animate-spin" : ""
                }`}
              >
                {meta.icon}
              </span>
              <span
                className={`text-sm flex-1 ${
                  step.status === "completed"
                    ? "text-[var(--color-text)]"
                    : step.status === "in_progress"
                      ? "text-[var(--color-primary)] font-medium"
                      : "text-[var(--color-text-secondary)]"
                }`}
              >
                {step.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              {step.progress && step.status === "in_progress" && (
                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                  {step.progress}
                </span>
              )}
              {step.completed_at && step.status === "completed" && (
                <span className="text-xs text-[var(--color-text-secondary)]">
                  {new Date(step.completed_at).toLocaleTimeString()}
                </span>
              )}
            </motion.div>
          );
        })}
      </div>
    </GlassCard>
  );
}

export const PipelineProgress = memo(PipelineProgressInner);
