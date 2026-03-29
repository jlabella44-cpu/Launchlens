"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import type { CreditTransaction, CreditBundle } from "@/lib/types";

const TIER_LABELS: Record<string, string> = {
  starter: "Lite",
  pro: "Active Agent",
  enterprise: "Team",
};

const TX_TYPE_STYLES: Record<string, { color: string; prefix: string }> = {
  purchase: { color: "text-green-600", prefix: "+" },
  bonus: { color: "text-green-600", prefix: "+" },
  rollover: { color: "text-blue-600", prefix: "" },
  usage: { color: "text-red-600", prefix: "-" },
  refund: { color: "text-green-600", prefix: "+" },
};

export default function BillingPage() {
  const { billingModel, creditBalance, tier, rolloverCap, refresh } = usePlan();
  const { toast } = useToast();

  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [bundles, setBundles] = useState<CreditBundle[]>([]);
  const [showBundles, setShowBundles] = useState(false);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        if (billingModel === "credit") {
          const [tx, b] = await Promise.all([
            apiClient.getCreditTransactions(),
            apiClient.getCreditBundles(),
          ]);
          setTransactions(tx);
          setBundles(b);
        }
      } catch {
        // Endpoints may not exist yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [billingModel]);

  async function handlePurchase(bundleId: string) {
    setPurchasing(bundleId);
    try {
      const { checkout_url } = await apiClient.purchaseCredits(
        parseInt(bundleId, 10),
        window.location.href,
        window.location.href,
      );
      window.location.href = checkout_url;
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Purchase failed", "error");
    } finally {
      setPurchasing(null);
    }
  }

  const tierLabel = TIER_LABELS[tier] || tier;

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-8"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Billing
        </h1>

        {billingModel === "credit" ? (
          <div className="space-y-8">
            {/* Credit Balance Hero */}
            <GlassCard tilt={false}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[var(--color-text-secondary)] mb-1">
                    Credit Balance
                  </p>
                  <motion.p
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="text-5xl font-bold text-[var(--color-primary)]"
                  >
                    {creditBalance ?? 0}
                  </motion.p>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-2">
                    {tierLabel} tier
                    {rolloverCap != null && (
                      <> &middot; Rollover cap: {rolloverCap} credits</>
                    )}
                  </p>
                </div>
                <Button onClick={() => setShowBundles(!showBundles)}>
                  Buy Credits
                </Button>
              </div>
            </GlassCard>

            {/* Credit Bundle Selection */}
            {showBundles && bundles.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <GlassCard tilt={false}>
                  <h2
                    className="text-lg font-semibold mb-4"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    Select a Credit Bundle
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {bundles.map((bundle) => (
                      <div
                        key={bundle.id}
                        className="border border-[var(--color-border)] rounded-xl p-4 text-center hover:border-[var(--color-primary)] transition-colors"
                      >
                        <p className="text-2xl font-bold text-[var(--color-text)]">
                          {bundle.credits}
                        </p>
                        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
                          credits
                        </p>
                        <p className="text-lg font-semibold mb-3">
                          ${(bundle.price_cents / 100).toFixed(2)}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)] mb-3">
                          {bundle.label}
                        </p>
                        <Button
                          onClick={() => handlePurchase(bundle.id)}
                          loading={purchasing === bundle.id}
                          className="w-full"
                        >
                          Buy
                        </Button>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {/* Transaction History */}
            <GlassCard tilt={false}>
              <h2
                className="text-lg font-semibold mb-4"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Transaction History
              </h2>
              {loading ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : transactions.length === 0 ? (
                <p className="text-sm text-[var(--color-text-secondary)] py-4">
                  No transactions yet.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                        <th className="pb-2 font-medium">Date</th>
                        <th className="pb-2 font-medium">Description</th>
                        <th className="pb-2 font-medium text-right">Credits</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => {
                        const style = TX_TYPE_STYLES[tx.type] || { color: "text-[var(--color-text)]", prefix: "" };
                        return (
                          <tr key={tx.id} className="border-b border-[var(--color-border)]/50">
                            <td className="py-3 text-[var(--color-text-secondary)]">
                              {new Date(tx.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3">{tx.description}</td>
                            <td className={`py-3 text-right font-medium ${style.color}`}>
                              {style.prefix}{Math.abs(tx.amount)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>
          </div>
        ) : (
          /* Legacy plan view */
          <GlassCard tilt={false}>
            <div className="text-center py-8">
              <p className="text-lg font-semibold text-[var(--color-text)]">
                Current Plan: <span className="text-[var(--color-primary)] capitalize">{tier}</span>
              </p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-2">
                Manage your subscription through the billing portal.
              </p>
              <Button className="mt-4" onClick={() => window.location.href = "/billing/portal"}>
                Manage Subscription
              </Button>
            </div>
          </GlassCard>
        )}
      </main>
    </>
  );
}
