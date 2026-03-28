"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";
import type {
  AdminStatsResponse,
  AdminTenantResponse,
  CreditSummaryResponse,
  TenantCreditsResponse,
  CreditTransactionResponse,
} from "@/lib/types";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <GlassCard tilt={false} className="text-center">
      <p className="text-2xl sm:text-3xl font-bold text-[var(--color-primary)]">{value}</p>
      <p className="text-xs sm:text-sm text-[var(--color-text-secondary)] mt-1">{label}</p>
    </GlassCard>
  );
}

function AdminDashboard() {
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [creditSummary, setCreditSummary] = useState<CreditSummaryResponse | null>(null);
  const [tenants, setTenants] = useState<AdminTenantResponse[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string | null>(null);
  const [tenantCredits, setTenantCredits] = useState<TenantCreditsResponse | null>(null);
  const [adjustAmount, setAdjustAmount] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjustLoading, setAdjustLoading] = useState(false);
  const [adjustError, setAdjustError] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "plan" | "credit_balance">("name");

  useEffect(() => {
    apiClient.adminStats().then(setStats).catch(console.error);
    apiClient.adminCreditsSummary().then(setCreditSummary).catch(console.error);
    apiClient.adminTenants().then(setTenants).catch(console.error);
  }, []);

  async function handleSelectTenant(tenantId: string) {
    setSelectedTenant(tenantId);
    setAdjustError("");
    try {
      const credits = await apiClient.adminTenantCredits(tenantId);
      setTenantCredits(credits);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleAdjust() {
    if (!selectedTenant || !adjustAmount || !adjustReason) return;
    setAdjustLoading(true);
    setAdjustError("");
    try {
      await apiClient.adminAdjustCredits(selectedTenant, parseInt(adjustAmount, 10), adjustReason);
      // Refresh data
      const credits = await apiClient.adminTenantCredits(selectedTenant);
      setTenantCredits(credits);
      apiClient.adminCreditsSummary().then(setCreditSummary).catch(console.error);
      apiClient.adminTenants().then(setTenants).catch(console.error);
      setAdjustAmount("");
      setAdjustReason("");
    } catch (err: any) {
      setAdjustError(err.message || "Adjustment failed");
    } finally {
      setAdjustLoading(false);
    }
  }

  const sortedTenants = [...tenants].sort((a, b) => {
    if (sortBy === "credit_balance") return (b.credit_balance ?? 0) - (a.credit_balance ?? 0);
    if (sortBy === "plan") return a.plan.localeCompare(b.plan);
    return a.name.localeCompare(b.name);
  });

  const selectedTenantName = tenants.find((t) => t.id === selectedTenant)?.name;

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        <h1
          className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-8"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Admin Dashboard
        </h1>

        {/* Platform Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="Tenants" value={stats?.total_tenants ?? "—"} />
          <StatCard label="Users" value={stats?.total_users ?? "—"} />
          <StatCard label="Listings" value={stats?.total_listings ?? "—"} />
          <StatCard
            label="Credits Outstanding"
            value={creditSummary?.total_credits_outstanding ?? "—"}
          />
        </div>

        {/* Credit Summary */}
        {creditSummary && (
          <GlassCard tilt={false} className="mb-8">
            <h2
              className="text-lg font-semibold mb-4"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Credit Summary (This Month)
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-[var(--color-text-secondary)]">Purchased</p>
                <p className="text-lg font-bold">{creditSummary.credits_purchased_this_month}</p>
              </div>
              <div>
                <p className="text-[var(--color-text-secondary)]">Used</p>
                <p className="text-lg font-bold">{creditSummary.credits_used_this_month}</p>
              </div>
              <div>
                <p className="text-[var(--color-text-secondary)]">Adjusted</p>
                <p className="text-lg font-bold">{creditSummary.credits_adjusted_this_month}</p>
              </div>
              <div>
                <p className="text-[var(--color-text-secondary)]">Tenants w/ Credits</p>
                <p className="text-lg font-bold">{creditSummary.tenant_count_with_credits}</p>
              </div>
            </div>
          </GlassCard>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Tenant Table */}
          <GlassCard tilt={false}>
            <div className="flex items-center justify-between mb-4">
              <h2
                className="text-lg font-semibold"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Tenants
              </h2>
              <select
                className="text-xs border border-[var(--color-border)] rounded px-2 py-1 bg-white"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              >
                <option value="name">Sort: Name</option>
                <option value="plan">Sort: Plan</option>
                <option value="credit_balance">Sort: Credits</option>
              </select>
            </div>
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full text-sm min-w-[400px]">
                <thead>
                  <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                    <th className="pb-2 font-medium px-4 sm:px-0">Name</th>
                    <th className="pb-2 font-medium">Plan</th>
                    <th className="pb-2 font-medium">Credits</th>
                    <th className="pb-2 font-medium pr-4 sm:pr-0"></th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTenants.map((t) => (
                    <tr
                      key={t.id}
                      className={`border-b border-[var(--color-border)]/50 cursor-pointer hover:bg-black/5 transition-colors ${
                        selectedTenant === t.id ? "bg-[var(--color-primary)]/5" : ""
                      }`}
                      onClick={() => handleSelectTenant(t.id)}
                    >
                      <td className="py-2.5 px-4 sm:px-0 font-medium truncate max-w-[150px]">
                        {t.name}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            t.plan === "enterprise"
                              ? "bg-purple-100 text-purple-700"
                              : t.plan === "pro"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {t.plan}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono">{t.credit_balance ?? 0}</td>
                      <td className="py-2.5 pr-4 sm:pr-0 text-[var(--color-primary)] text-xs">
                        View
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>

          {/* Credit Detail + Adjustment */}
          <div className="space-y-6">
            {selectedTenant && tenantCredits ? (
              <>
                <GlassCard tilt={false}>
                  <h2
                    className="text-lg font-semibold mb-1"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    {selectedTenantName}
                  </h2>
                  <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                    Balance:{" "}
                    <span className="font-bold text-[var(--color-primary)] text-lg">
                      {tenantCredits.credit_balance}
                    </span>{" "}
                    credits
                  </p>

                  {/* Adjustment Form */}
                  <div className="border-t border-[var(--color-border)] pt-4 mt-4">
                    <h3 className="text-sm font-semibold mb-3">Adjust Credits</h3>
                    <div className="flex flex-col sm:flex-row gap-3 mb-3">
                      <input
                        type="number"
                        placeholder="Amount (e.g. 5 or -3)"
                        value={adjustAmount}
                        onChange={(e) => setAdjustAmount(e.target.value)}
                        className="flex-1 px-3 py-2 border border-[var(--color-border)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                      />
                      <input
                        type="text"
                        placeholder="Reason"
                        value={adjustReason}
                        onChange={(e) => setAdjustReason(e.target.value)}
                        className="flex-[2] px-3 py-2 border border-[var(--color-border)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                      />
                    </div>
                    <Button
                      onClick={handleAdjust}
                      loading={adjustLoading}
                      disabled={!adjustAmount || !adjustReason}
                      variant="secondary"
                    >
                      Apply Adjustment
                    </Button>
                    {adjustError && (
                      <p className="text-sm text-[var(--color-error)] mt-2">{adjustError}</p>
                    )}
                  </div>
                </GlassCard>

                {/* Transaction History */}
                <GlassCard tilt={false}>
                  <h3
                    className="text-sm font-semibold mb-3"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    Recent Transactions
                  </h3>
                  {tenantCredits.transactions.length === 0 ? (
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      No credit transactions yet.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {tenantCredits.transactions.map((txn) => (
                        <div
                          key={txn.id}
                          className="flex items-start justify-between py-2 border-b border-[var(--color-border)]/30 last:border-0"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-xs px-1.5 py-0.5 rounded ${
                                  txn.transaction_type === "purchase"
                                    ? "bg-green-100 text-green-700"
                                    : txn.transaction_type === "usage"
                                    ? "bg-orange-100 text-orange-700"
                                    : txn.transaction_type === "admin_adjustment"
                                    ? "bg-blue-100 text-blue-700"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                              >
                                {txn.transaction_type.replace("_", " ")}
                              </span>
                              <span className="text-xs text-[var(--color-text-secondary)]">
                                {new Date(txn.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            {txn.reason && (
                              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 truncate">
                                {txn.reason}
                              </p>
                            )}
                          </div>
                          <div className="text-right ml-3">
                            <span
                              className={`text-sm font-mono font-bold ${
                                txn.amount > 0 ? "text-green-600" : "text-red-500"
                              }`}
                            >
                              {txn.amount > 0 ? "+" : ""}
                              {txn.amount}
                            </span>
                            <p className="text-xs text-[var(--color-text-secondary)]">
                              bal: {txn.balance_after}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </GlassCard>
              </>
            ) : (
              <GlassCard tilt={false}>
                <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
                  Select a tenant to view credit details and make adjustments.
                </p>
              </GlassCard>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

export default function AdminPage() {
  return (
    <ProtectedRoute>
      <AdminDashboard />
    </ProtectedRoute>
  );
}
