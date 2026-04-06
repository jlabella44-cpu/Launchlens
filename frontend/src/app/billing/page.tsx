"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import { trackEvent, AnalyticsEvents } from "@/lib/analytics";
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

/** Live counter showing remaining Founding 200 spots. */
function FoundingCounter() {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    // Try to fetch from API; fallback to a placeholder
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/founding/remaining`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.remaining != null) setRemaining(data.remaining); })
      .catch(() => { /* endpoint may not exist yet — show nothing */ });
  }, []);

  if (remaining == null) return null;

  return (
    <div className="flex flex-col items-center">
      <motion.p
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        className="text-3xl font-bold text-[#F97316]"
      >
        {remaining}
      </motion.p>
      <p className="text-[10px] text-white/40 uppercase tracking-wider">Spots remaining</p>
    </div>
  );
}

/** Referral link share widget with copy-to-clipboard. */
function ReferralShareWidget() {
  const [copied, setCopied] = useState(false);
  const [code, setCode] = useState<string | null>(null);

  useEffect(() => {
    // Try to fetch user's referral code
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/referral/code`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("listingjet_token") || ""}`,
      },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.code) setCode(data.code); })
      .catch(() => { /* endpoint may not exist yet */ });
  }, []);

  const referralUrl = code
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/register?ref=${code}`
    : null;

  function handleCopy() {
    if (!referralUrl) return;
    navigator.clipboard.writeText(referralUrl);
    setCopied(true);
    trackEvent(AnalyticsEvents.REFERRAL_SENT, { code: code || "" });
    setTimeout(() => setCopied(false), 2000);
  }

  if (!referralUrl) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">
        Your referral link will appear here once your account is fully activated.
      </p>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        readOnly
        value={referralUrl}
        className="flex-1 px-4 py-2.5 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text)] truncate"
      />
      <button
        onClick={handleCopy}
        className="px-4 py-2.5 rounded-lg bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors whitespace-nowrap"
      >
        {copied ? "Copied!" : "Copy Link"}
      </button>
    </div>
  );
}

function BillingContent() {
  const { billingModel, creditBalance, tier, rolloverCap } = usePlan();
  const { toast } = useToast();

  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [bundles, setBundles] = useState<CreditBundle[]>([]);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { document.title = "Credits & Billing | ListingJet"; }, []);

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
      const parsed = new URL(checkout_url);
      if (!parsed.hostname.endsWith("stripe.com")) throw new Error("Invalid checkout URL");
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
        <p className="text-sm text-[var(--color-text-secondary)] mb-8">
          Manage your mission fuel and transaction history.
        </p>

        {billingModel === "credit" ? (
          <div className="space-y-8">
            {/* Credit Balance Hero */}
            <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
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
                  <span className="text-lg font-normal text-[var(--color-text-secondary)] ml-2 uppercase tracking-wider">Credits</span>
                </motion.p>
                {rolloverCap != null && (
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-border)]" />
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
              <p className="text-xs text-[var(--color-text-secondary)] mb-4">Choose your mission fuel capacity.</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {bundles.map((bundle, i) => {
                  const isRecommended = i === 2;
                  return (
                    <div
                      key={bundle.id}
                      className={`rounded-2xl p-5 text-center transition-all ${
                        isRecommended
                          ? "bg-[#0B1120] text-white ring-2 ring-[#F97316]"
                          : "bg-[var(--color-surface)] border border-[var(--color-card-border)]"
                      }`}
                    >
                      {isRecommended && (
                        <span className="text-[9px] font-bold uppercase tracking-widest text-[#F97316] mb-1 block">
                          Best Value
                        </span>
                      )}
                      <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                        {BUNDLE_NAMES[i] || `Bundle ${i + 1}`}
                      </p>
                      <p className={`text-3xl font-bold ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                        {bundle.credits}
                      </p>
                      <p className={`text-xs mb-1 ${isRecommended ? "text-white/60" : "text-[var(--color-text-secondary)]"}`}>Credits</p>
                      <p className={`text-lg font-bold mb-0.5 ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                        ${(bundle.price_cents / 100).toFixed(0)}
                      </p>
                      <p className={`text-[10px] mb-3 ${isRecommended ? "text-white/50" : "text-[var(--color-text-secondary)]"}`}>
                        ${(bundle.per_credit_cents / 100).toFixed(0)}/credit
                      </p>
                      <button
                        onClick={() => handlePurchase(bundle.id)}
                        disabled={purchasing === bundle.id}
                        className={`w-full py-2 rounded-full text-xs font-semibold transition-colors disabled:opacity-50 ${
                          isRecommended
                            ? "bg-[#F97316] hover:bg-[#ea580c] text-white"
                            : "border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-secondary)]"
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
            <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
              <div className="flex items-center justify-between mb-4">
                <h2
                  className="text-lg font-bold text-[var(--color-text)]"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Flight Logs
                </h2>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-[var(--color-text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </div>
              </div>

              {loading ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : transactions.length === 0 ? (
                <p className="text-sm text-[var(--color-text-secondary)] py-4 text-center">
                  No transactions yet.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold border-b border-[var(--color-card-border)]">
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
                          <tr key={tx.id} className="border-b border-[var(--color-card-border)]">
                            <td className="py-3 text-[var(--color-text-secondary)]">
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
                    <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider cursor-pointer hover:text-[var(--color-text)]">
                      View Full Archive
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-8 text-center">
            <p className="text-lg font-semibold text-[var(--color-text)]">
              Current Plan: <span className="text-[#F97316] capitalize">{tier}</span>
            </p>
            <p className="text-sm text-[var(--color-text-secondary)] mt-2 mb-4">
              Manage your subscription through the billing portal.
            </p>
            <button
              onClick={async () => {
                try {
                  const { portal_url } = await apiClient.billingPortal(window.location.href);
                  window.location.href = portal_url;
                } catch (err: unknown) {
                  alert(err instanceof Error ? err.message : "Failed to open billing portal");
                }
              }}
              className="px-6 py-3 rounded-full border border-[var(--color-border)] text-sm font-semibold text-[var(--color-text-secondary)] hover:border-amber-400 hover:text-amber-600 hover:shadow-lg hover:shadow-amber-500/10 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
            >
              Manage Subscription
            </button>
          </div>
        )}

        {/* Founding 200 Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-[#0B1120] to-[#1a2744] rounded-2xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        >
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#F97316]">Founding 200</span>
            </div>
            <p className="text-white font-bold text-lg" style={{ fontFamily: "var(--font-heading)" }}>
              Lock in 30% off for life
            </p>
            <p className="text-sm text-white/50 mt-1">
              Be one of the first 200 subscribers and keep founding pricing forever.
            </p>
          </div>
          <div className="text-center">
            <FoundingCounter />
          </div>
        </motion.div>

        {/* Share & Earn */}
        <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
          <h2
            className="text-lg font-bold text-[var(--color-text)] mb-1"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Share &amp; Earn
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mb-4">
            Give a friend 30 credits, get 30 credits when they sign up.
          </p>
          <ReferralShareWidget />
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-[var(--color-card-border)] flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
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
