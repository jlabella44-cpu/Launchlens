"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import apiClient from "@/lib/api-client";
import type {
  AdminStatsResponse,
  AdminTenantResponse,
  CreditSummaryResponse,
  TenantCreditsResponse,
} from "@/lib/types";

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
  const [search, setSearch] = useState("");

  useEffect(() => { document.title = "Admin Dashboard | ListingJet"; }, []);

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

  const sortedTenants = [...tenants]
    .filter((t) => !search || t.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === "credit_balance") return (b.credit_balance ?? 0) - (a.credit_balance ?? 0);
      if (sortBy === "plan") return a.plan.localeCompare(b.plan);
      return a.name.localeCompare(b.name);
    });

  const selectedTenantData = tenants.find((t) => t.id === selectedTenant);

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        {/* Header */}
        <h1
          className="text-3xl font-bold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Admin Dashboard
        </h1>
        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold mb-8">
          Flight Level: Command Center Ops
        </p>

        {/* Platform Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Tenants", value: stats?.total_tenants ?? "—", suffix: "active" },
            { label: "Users", value: stats?.total_users ?? "—", suffix: "total" },
            { label: "Listings", value: stats?.total_listings ?? "—", suffix: "Supersonic" },
            { label: "Credits Outstanding", value: creditSummary?.total_credits_outstanding ?? "—", suffix: "" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-2xl border border-slate-100 p-5 text-center">
              <p className="text-3xl font-bold text-[var(--color-text)]">
                {typeof s.value === "number" ? s.value.toLocaleString() : s.value}
              </p>
              <p className="text-xs text-slate-400 mt-1">{s.label}</p>
              {s.suffix && (
                <span className="inline-flex mt-1 text-[9px] uppercase tracking-wider font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                  {s.suffix}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Global Credit Ledger */}
        {creditSummary && (
          <div className="bg-[#0B1120] rounded-2xl p-6 mb-8">
            <p className="text-[10px] uppercase tracking-widest text-white/40 font-semibold mb-4">
              Global Credit Ledger
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
              {[
                { label: "Purchased", value: creditSummary.credits_purchased_this_month },
                { label: "Used", value: creditSummary.credits_used_this_month },
                { label: "Adjusted", value: `+${creditSummary.credits_adjusted_this_month}` },
                { label: "Tenants", value: creditSummary.tenant_count_with_credits },
              ].map((m) => (
                <div key={m.label}>
                  <p className="text-[10px] uppercase tracking-wider text-white/40">{m.label}</p>
                  <p className="text-2xl font-bold text-white">{typeof m.value === "number" ? m.value.toLocaleString() : m.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Two-column: Tenant Table + Credit Detail */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Left: Tenant Roster */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2
                  className="text-lg font-bold text-[var(--color-text)]"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Tenant Roster
                </h2>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <svg className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                      type="text"
                      placeholder="Search..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 w-32"
                    />
                  </div>
                  <select
                    className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                  >
                    <option value="name">Name</option>
                    <option value="plan">Plan</option>
                    <option value="credit_balance">Credits</option>
                  </select>
                </div>
              </div>

              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold border-b border-slate-100">
                    <th className="pb-2 text-left">Name</th>
                    <th className="pb-2 text-left">Plan</th>
                    <th className="pb-2 text-left">Credit Balance</th>
                    <th className="pb-2 text-left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTenants.map((t) => (
                    <tr
                      key={t.id}
                      className={`border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition-colors ${
                        selectedTenant === t.id ? "bg-[#F97316]/5" : ""
                      }`}
                      onClick={() => handleSelectTenant(t.id)}
                    >
                      <td className="py-3 font-medium truncate max-w-[180px]">
                        {selectedTenant === t.id && (
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#F97316] mr-2" />
                        )}
                        {t.name}
                      </td>
                      <td className="py-3">
                        <span className={`text-[10px] px-2 py-0.5 rounded uppercase tracking-wider font-bold ${
                          t.plan === "enterprise" ? "bg-purple-100 text-purple-700"
                            : t.plan === "pro" ? "bg-blue-100 text-blue-700"
                            : "bg-slate-100 text-slate-500"
                        }`}>
                          {t.plan}
                        </span>
                      </td>
                      <td className="py-3 font-mono font-bold">{t.credit_balance?.toLocaleString() ?? 0}</td>
                      <td className="py-3 text-[#F97316] text-xs font-semibold uppercase tracking-wider">View</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right: Credit Detail */}
          <div className="lg:col-span-2 space-y-6">
            {selectedTenant && tenantCredits && selectedTenantData ? (
              <>
                {/* Tenant Info */}
                <div className="bg-white rounded-2xl border border-slate-100 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-500">
                      {selectedTenantData.name.charAt(0)}
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--color-text)]">{selectedTenantData.name}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider">Active Tenant Since {new Date(selectedTenantData.created_at).getFullYear()}</p>
                    </div>
                  </div>

                  <div className="bg-[#F97316]/10 rounded-xl p-4 mb-4">
                    <p className="text-[10px] uppercase tracking-wider text-[#F97316] font-semibold mb-1">Credit Balance</p>
                    <p className="text-3xl font-bold text-[var(--color-text)]">
                      {tenantCredits.credit_balance?.toLocaleString()}
                    </p>
                  </div>

                  {/* Adjustment Form */}
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                    Credit Adjustment
                  </p>
                  <div className="space-y-2 mb-3">
                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">Adjustment Amount</label>
                      <input
                        type="number"
                        placeholder="e.g. 500 or -500"
                        value={adjustAmount}
                        onChange={(e) => setAdjustAmount(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">Reason for Adjustment</label>
                      <input
                        type="text"
                        placeholder="Service compensation, promo code, etc."
                        value={adjustReason}
                        onChange={(e) => setAdjustReason(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleAdjust}
                    disabled={adjustLoading || !adjustAmount || !adjustReason}
                    className="w-full py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold disabled:opacity-50 transition-colors"
                  >
                    {adjustLoading ? "Applying..." : "Apply Adjustment"}
                  </button>
                  {adjustError && (
                    <p className="text-xs text-red-500 mt-2">{adjustError}</p>
                  )}
                </div>

                {/* Recent Transactions */}
                <div className="bg-white rounded-2xl border border-slate-100 p-5">
                  <h3 className="text-sm font-bold text-[var(--color-text)] uppercase tracking-wider mb-3">
                    Recent Transactions
                  </h3>
                  {tenantCredits.transactions.length === 0 ? (
                    <p className="text-sm text-slate-400">No transactions yet.</p>
                  ) : (
                    <div className="space-y-3 max-h-[350px] overflow-y-auto">
                      {tenantCredits.transactions.map((txn) => (
                        <div key={txn.id} className="flex items-center justify-between">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm text-[var(--color-text)]">
                              {txn.amount > 0 ? "+" : ""}{txn.amount}
                            </p>
                            <p className="text-[10px] text-slate-400">
                              {txn.reason || txn.description || txn.transaction_type}
                            </p>
                          </div>
                          <span className={`text-[9px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${
                            txn.amount > 0 ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"
                          }`}>
                            {txn.amount > 0 ? "Processing" : "Depletion"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-100 p-8 text-center">
                <p className="text-sm text-slate-400">
                  Select a tenant to view credit details and make adjustments.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-slate-100 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-300">
          <span>ListingJet Command</span>
          <span>© {new Date().getFullYear()} ListingJet. System Status: Supersonic.</span>
          <div className="flex gap-6">
            <span>Privacy</span>
            <span>Security</span>
            <span>Support</span>
          </div>
        </footer>
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
