"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import type { Invoice, UsageResponse } from "@/lib/types";

const PLAN_NAMES: Record<string, string> = {
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
};

function BillingDashboard() {
  const { plan, limits } = usePlan();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    apiClient
      .billingInvoices(5)
      .then((res) => setInvoices(res.invoices))
      .catch(() => {});
    apiClient
      .getUsage()
      .then(setUsage)
      .catch(() => {});
  }, []);

  async function handleManageBilling() {
    setPortalLoading(true);
    try {
      const res = await apiClient.billingPortal(window.location.href);
      window.location.href = res.portal_url;
    } catch (err: any) {
      alert(err.message || "Could not open billing portal");
    } finally {
      setPortalLoading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8">
        <h1
          className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-8"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Billing
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Current Plan */}
          <GlassCard tilt={false}>
            <h2
              className="text-lg font-semibold mb-4"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Current Plan
            </h2>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl font-bold text-[var(--color-primary)]">
                {PLAN_NAMES[plan] || plan}
              </span>
              {plan !== "enterprise" && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                  {plan === "starter" ? "Free Tier" : "Active"}
                </span>
              )}
            </div>
            <ul className="text-sm text-[var(--color-text-secondary)] space-y-1.5 mb-6">
              <li>{limits.max_listings_per_month} listings/month</li>
              <li>{limits.max_assets_per_listing} photos/listing</li>
              <li>AI Vision Tier 2: {limits.tier2_vision ? "Included" : "Not included"}</li>
              <li>Social Content: {limits.social_content ? "Included" : "Not included"}</li>
            </ul>
            <div className="flex flex-col sm:flex-row gap-3">
              <Button onClick={handleManageBilling} loading={portalLoading} variant="secondary">
                Manage Subscription
              </Button>
              {plan === "starter" && (
                <Button onClick={() => (window.location.href = "/pricing")}>
                  Upgrade Plan
                </Button>
              )}
            </div>
          </GlassCard>

          {/* Usage */}
          <GlassCard tilt={false}>
            <h2
              className="text-lg font-semibold mb-4"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Usage This Month
            </h2>
            {usage ? (
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-[var(--color-text-secondary)]">Listings</span>
                    <span className="font-medium">
                      {usage.listings_this_month} / {limits.max_listings_per_month}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-primary)] rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (usage.listings_this_month / limits.max_listings_per_month) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
                <div className="text-sm text-[var(--color-text-secondary)]">
                  <p>Total listings: {usage.total_listings}</p>
                  <p>Total assets: {usage.total_assets}</p>
                </div>
              </div>
            ) : (
              <div className="h-20 flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </GlassCard>
        </div>

        {/* Invoices */}
        <GlassCard tilt={false}>
          <h2
            className="text-lg font-semibold mb-4"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Recent Invoices
          </h2>
          {invoices.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">
              No invoices yet.
            </p>
          ) : (
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full text-sm min-w-[400px]">
                <thead>
                  <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                    <th className="pb-2 font-medium px-4 sm:px-0">Date</th>
                    <th className="pb-2 font-medium">Amount</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium pr-4 sm:pr-0"></th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-[var(--color-border)]/50">
                      <td className="py-2.5 px-4 sm:px-0">
                        {new Date(inv.created * 1000).toLocaleDateString()}
                      </td>
                      <td className="py-2.5">
                        ${(inv.amount_paid / 100).toFixed(2)} {inv.currency.toUpperCase()}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            inv.status === "paid"
                              ? "bg-green-100 text-green-700"
                              : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 sm:pr-0">
                        {inv.hosted_invoice_url && (
                          <a
                            href={inv.hosted_invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[var(--color-primary)] hover:underline"
                          >
                            View
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      </main>
    </>
  );
}

export default function BillingPage() {
  return (
    <ProtectedRoute>
      <BillingDashboard />
    </ProtectedRoute>
  );
}
