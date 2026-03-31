"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import type { CreditTransaction, CreditBundle } from "@/lib/types";

const TIER_LABELS: Record<string, string> = {
  starter: "Lite",
  pro: "Active Agent",
  enterprise: "Team",
};

const BUNDLE_NAMES = ["Solo Mission", "Squadron", "Air Wing", "Global Fleet"];

const TX_TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  purchase: { bg: "bg-green-50", text: "text-green-700", label: "Confirmed" },
  bonus: { bg: "bg-green-50", text: "text-green-700", label: "Confirmed" },
  rollover: { bg: "bg-blue-50", text: "text-blue-700", label: "Adjustment" },
  usage: { bg: "bg-red-50", text: "text-red-600", label: "Deployed" },
  refund: { bg: "bg-green-50", text: "text-green-700", label: "Confirmed" },
};

function BillingContent() {
  const { billingModel, creditBalance, tier, rolloverCap } = usePlan();
  const { toast } = useToast();

  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [bundles, setBundles] = useState<CreditBundle[]>([]);
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
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Header */}
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-1"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Credits &amp; Billing
        </h1>
        <p className="text-sm text-slate-400 mb-8">
          Manage your mission fuel and transaction history.
        </p>

        {billingModel === "credit" ? (
          <div className="space-y-8">
            {/* Credit Balance Hero */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest bg-[#F97316]/10 text-[#F97316] mb-2">
                  {tierLabel} Tier
                </span>
                <motion.p
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-5xl font-bold text-[var(--color-text)]"
                >
                  {creditBalance ?? 0}
                  <span className="text-lg font-normal text-slate-400 ml-2 uppercase tracking-wider">Credits</span>
                </motion.p>
                {rolloverCap != null && (
                  <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                    {rolloverCap} credits rollover cap
                  </p>
                )}
              </div>
              <button
                onClick={() => {
                  const el = document.getElementById("bundles");
                  el?.scrollIntoView({ behavior: "smooth" });
                }}
                className="px-6 py-3 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors shadow-lg shadow-orange-200 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Buy Credits
              </button>
            </div>

            {/* Credit Bundles */}
            <div id="bundles">
              <h2
                className="text-xl font-bold text-[var(--color-text)] mb-1"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Pre-Flight Refueling
              </h2>
              <p className="text-xs text-slate-400 mb-4">Choose your mission fuel capacity.</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {bundles.map((bundle, i) => {
                  const isRecommended = i === 2;
                  return (
                    <div
                      key={bundle.id}
                      className={`rounded-2xl p-5 text-center transition-all ${
                        isRecommended
                          ? "bg-[#0B1120] text-white ring-2 ring-[#F97316]"
                          : "bg-white border border-slate-100"
                      }`}
                    >
                      {isRecommended && (
                        <span className="text-[9px] font-bold uppercase tracking-widest text-[#F97316] mb-1 block">
                          Best Value
                        </span>
                      )}
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">
                        {BUNDLE_NAMES[i] || `Bundle ${i + 1}`}
                      </p>
                      <p className={`text-3xl font-bold ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                        {bundle.credits}
                      </p>
                      <p className={`text-xs mb-1 ${isRecommended ? "text-white/60" : "text-slate-400"}`}>Credits</p>
                      <p className={`text-lg font-bold mb-0.5 ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                        ${(bundle.price_cents / 100).toFixed(0)}
                      </p>
                      <p className={`text-[10px] mb-3 ${isRecommended ? "text-white/50" : "text-slate-400"}`}>
                        ${(bundle.per_credit_cents / 100).toFixed(0)}/credit
                      </p>
                      <button
                        onClick={() => handlePurchase(bundle.id)}
                        disabled={purchasing === bundle.id}
                        className={`w-full py-2 rounded-full text-xs font-semibold transition-colors disabled:opacity-50 ${
                          isRecommended
                            ? "bg-[#F97316] hover:bg-[#ea580c] text-white"
                            : "border border-slate-200 text-slate-600 hover:border-slate-300"
                        }`}
                      >
                        {purchasing === bundle.id ? "..." : "Purchase"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Flight Logs (Transaction History) */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2
                  className="text-lg font-bold text-[var(--color-text)]"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Flight Logs
                </h2>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </div>
              </div>

              {loading ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : transactions.length === 0 ? (
                <p className="text-sm text-slate-400 py-4 text-center">
                  No transactions yet.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold border-b border-slate-100">
                        <th className="pb-3 text-left">Date</th>
                        <th className="pb-3 text-left">Description</th>
                        <th className="pb-3 text-right">Credits</th>
                        <th className="pb-3 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => {
                        const style = TX_TYPE_STYLES[tx.type] || TX_TYPE_STYLES[tx.transaction_type] || { bg: "bg-slate-50", text: "text-slate-600", label: "—" };
                        const isPositive = tx.amount > 0;
                        return (
                          <tr key={tx.id} className="border-b border-slate-50">
                            <td className="py-3 text-slate-400">
                              {new Date(tx.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                            </td>
                            <td className="py-3 text-[var(--color-text)]">
                              {tx.description || "Transaction"}
                            </td>
                            <td className={`py-3 text-right font-bold ${isPositive ? "text-green-600" : "text-red-500"}`}>
                              {isPositive ? "+" : ""}{tx.amount}
                            </td>
                            <td className="py-3 text-right">
                              <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}>
                                {style.label}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  <div className="text-center pt-4">
                    <span className="text-xs text-slate-300 uppercase tracking-wider cursor-pointer hover:text-slate-400">
                      View Full Archive
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-100 p-8 text-center">
            <p className="text-lg font-semibold text-[var(--color-text)]">
              Current Plan: <span className="text-[#F97316] capitalize">{tier}</span>
            </p>
            <p className="text-sm text-slate-400 mt-2 mb-4">
              Manage your subscription through the billing portal.
            </p>
            <button
              onClick={() => { window.location.href = "/billing/portal"; }}
              className="px-6 py-3 rounded-full border border-slate-200 text-sm font-semibold text-slate-600 hover:border-slate-300 transition-colors"
            >
              Manage Subscription
            </button>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-slate-100 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-300">
          <span>ListingJet</span>
          <div className="flex gap-6">
            <span>Ground Control</span>
            <span>Flight Manual</span>
            <span>Privacy Protocol</span>
            <span>Terms of Service</span>
          </div>
          <span>© {new Date().getFullYear()} ListingJet. All rights reserved.</span>
        </footer>
      </main>
    </>
  );
}

export default function BillingPage() {
  return (
    <ProtectedRoute>
      <BillingContent />
    </ProtectedRoute>
  );
}
