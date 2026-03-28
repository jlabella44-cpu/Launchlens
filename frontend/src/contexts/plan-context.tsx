"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useAuth } from "./auth-context";
import apiClient from "@/lib/api-client";
import type { PlanLimits } from "@/lib/types";

const PLAN_LIMITS: Record<string, PlanLimits> = {
  starter: {
    max_listings_per_month: 5,
    max_assets_per_listing: 25,
    tier2_vision: false,
    social_content: false,
  },
  pro: {
    max_listings_per_month: 50,
    max_assets_per_listing: 50,
    tier2_vision: true,
    social_content: true,
  },
  enterprise: {
    max_listings_per_month: 500,
    max_assets_per_listing: 100,
    tier2_vision: true,
    social_content: true,
  },
};

interface PlanContextValue {
  plan: string;
  limits: PlanLimits;
  loading: boolean;
  isFeatureGated: (feature: "tier2_vision" | "social_content") => boolean;
}

const PlanContext = createContext<PlanContextValue | null>(null);

export function PlanProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [plan, setPlan] = useState("starter");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    apiClient
      .billingStatus()
      .then((res) => setPlan(res.plan || "starter"))
      .catch(() => setPlan("starter"))
      .finally(() => setLoading(false));
  }, [user]);

  const limits = PLAN_LIMITS[plan] || PLAN_LIMITS.starter;

  function isFeatureGated(feature: "tier2_vision" | "social_content") {
    return !limits[feature];
  }

  return (
    <PlanContext.Provider value={{ plan, limits, loading, isFeatureGated }}>
      {children}
    </PlanContext.Provider>
  );
}

export function usePlan() {
  const ctx = useContext(PlanContext);
  if (!ctx) throw new Error("usePlan must be used within PlanProvider");
  return ctx;
}
