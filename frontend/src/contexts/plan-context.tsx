"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import apiClient from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import type { CreditBalance, BillingStatus } from "@/lib/types";

interface PlanContextValue {
  // Plan fields
  plan: string;
  tier: string;

  // Credit billing fields
  billingModel: "legacy" | "credit";
  creditBalance: number | null;
  grantedBalance: number | null;
  purchasedBalance: number | null;
  canAffordListing: boolean;
  listingCreditCost: number;
  rolloverCap: number | null;

  // State
  loading: boolean;
  refresh: () => Promise<void>;
}

const PlanContext = createContext<PlanContextValue | null>(null);

const LISTING_CREDIT_COST = 12; // v3: weighted credit cost for base listing

export function PlanProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [creditData, setCreditData] = useState<CreditBalance | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPlanData = useCallback(async () => {
    if (!user) {
      setLoading(false);
      return;
    }

    try {
      const status = await apiClient.billingStatus();
      setBillingStatus(status);

      if (status.billing_model === "credit") {
        const balance = await apiClient.getCreditBalance();
        setCreditData(balance);
      }
    } catch {
      // Billing endpoints may not be available yet — use defaults
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchPlanData();
  }, [fetchPlanData]);

  const plan = billingStatus?.plan ?? "free";
  const tier = billingStatus?.tier ?? creditData?.tier ?? plan;
  const billingModel = (billingStatus?.billing_model ?? "legacy") as "legacy" | "credit";
  const listingCreditCost = LISTING_CREDIT_COST;
  const creditBalance = creditData?.balance ?? null;
  const grantedBalance = creditData?.granted_balance ?? null;
  const purchasedBalance = creditData?.purchased_balance ?? null;
  const canAffordListing = creditBalance !== null ? creditBalance >= listingCreditCost : true;
  const rolloverCap = creditData?.rollover_cap ?? null;

  return (
    <PlanContext.Provider
      value={{
        plan,
        tier,
        billingModel,
        creditBalance,
        grantedBalance,
        purchasedBalance,
        canAffordListing,
        listingCreditCost,
        rolloverCap,
        loading,
        refresh: fetchPlanData,
      }}
    >
      {children}
    </PlanContext.Provider>
  );
}

export function usePlan() {
  const ctx = useContext(PlanContext);
  if (!ctx) throw new Error("usePlan must be used within PlanProvider");
  return ctx;
}
