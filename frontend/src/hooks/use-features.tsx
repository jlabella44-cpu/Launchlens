"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import apiClient from "@/lib/api-client";

export type FeatureName =
  | "learning"
  | "health_score"
  | "performance_intelligence"
  | "help_agent"
  | "microsite"
  | "webhooks"
  | "listing_permissions";

export function parseFeatures(body: { features?: string[] } | undefined): Set<FeatureName> {
  return new Set((body?.features ?? []) as FeatureName[]);
}

const FeaturesContext = createContext<Set<FeatureName>>(new Set());

export function FeaturesProvider({ children, enabled }: { children: ReactNode; enabled?: boolean }) {
  const [features, setFeatures] = useState<Set<FeatureName>>(new Set());

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    apiClient
      .getFeatures()
      .then((body) => {
        if (!cancelled) setFeatures(parseFeatures(body));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return <FeaturesContext.Provider value={features}>{children}</FeaturesContext.Provider>;
}

export function useFeature(name: FeatureName): boolean {
  return useContext(FeaturesContext).has(name);
}
