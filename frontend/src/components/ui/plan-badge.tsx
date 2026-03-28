"use client";

import { usePlan } from "@/contexts/plan-context";

interface PlanBadgeProps {
  feature: "tier2_vision" | "social_content";
  label?: string;
}

/**
 * Shows a "Pro" badge next to plan-gated features for Starter users.
 * Renders nothing if the user's plan already includes the feature.
 */
export function PlanBadge({ feature, label = "Pro" }: PlanBadgeProps) {
  const { isFeatureGated } = usePlan();

  if (!isFeatureGated(feature)) return null;

  return <span className="plan-badge">{label}</span>;
}
