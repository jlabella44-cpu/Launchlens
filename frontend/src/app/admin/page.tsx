"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Badge } from "@/components/ui/badge";
import apiClient from "@/lib/api-client";
import type {
  AdminStatsResponse,
  AdminTenantResponse,
  AdminListingItem,
  AdminUserItem,
  AuditLogEntry,
  SystemEvent,
  RevenueBreakdownResponse,
  CreditSummaryResponse,
  TenantCreditsResponse,
} from "@/lib/types";

type Tab = "overview" | "tenants" | "listings" | "credits" | "audit" | "support";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "tenants", label: "Tenants" },
  { key: "listings", label: "Listings" },
  { key: "credits", label: "Credits" },
  { key: "audit", label: "Audit Log" },
  { key: "support", label: "Support" },
];

// ---------------------------------------------------------------------------
// Helper: plan badge color
// ---------------------------------------------------------------------------
function planColor(plan: string) {
  if (plan === "enterprise") return "bg-purple-100 text-purple-700";
  if (plan === "pro") return "bg-blue-100 text-blue-700";
  return "bg-slate-100 text-slate-500";
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("overview");
  useEffect(() => { document.title = "Admin Dashboard | ListingJet"; }, []);

  return (
    <ProtectedRoute>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        <h1 className="text-3xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
          Admin Dashboard
        </h1>
        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold mb-6">
          Flight Level: Command Center Ops
        </p>

        {/* Tab bar */}
        <div className="flex gap-1.5 mb-8 overflow-x-auto pb-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-colors whitespace-nowrap ${
                tab === t.key
                  ? "bg-[#F97316] text-white"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "overview" && <OverviewTab onNavigate={setTab} />}
        {tab === "tenants" && <TenantsTab />}
        {tab === "listings" && <ListingsTab />}
        {tab === "credits" && <CreditsTab />}
        {tab === "audit" && <AuditTab />}
        {tab === "support" && <SupportTab />}
      </main>
    </ProtectedRoute>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Overview
// ═══════════════════════════════════════════════════════════════════════════
function OverviewTab({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [creditSummary, setCreditSummary] = useState<CreditSummaryResponse | null>(null);
  const [revenue, setRevenue] = useState<RevenueBreakdownResponse | null>(null);
  const [events, setEvents] = useState<SystemEvent[]>([]);

  useEffect(() => {
    apiClient.adminStats().then(setStats).catch(console.error);
    apiClient.adminCreditsSummary().then(setCreditSummary).catch(console.error);
    apiClient.adminRevenue().then(setRevenue).catch(console.error);
    apiClient.adminRecentEvents({ limit: 10 }).then(setEvents).catch(console.error);
  }, []);

  const failedCount = (stats?.listings_by_state?.failed ?? 0) + (stats?.listings_by_state?.pipeline_timeout ?? 0);

  return (
    <div className="space-y-8">
      {/* Alert: Attention Required */}
      {failedCount > 0 && (
        <button
          onClick={() => onNavigate("listings")}
          className="w-full bg-red-50 border border-red-200 rounded-2xl p-4 text-left hover:bg-red-100 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-red-700">{failedCount} listing{failedCount > 1 ? "s" : ""} need attention</p>
              <p className="text-xs text-red-500">Click to view failed and timed-out listings</p>
            </div>
          </div>
        </button>
      )}

      {/* Platform Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Tenants", value: stats?.total_tenants ?? "—" },
          { label: "Users", value: stats?.total_users ?? "—" },
          { label: "Listings", value: stats?.total_listings ?? "—" },
          { label: "Credits Outstanding", value: creditSummary?.total_credits_outstanding ?? "—" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-2xl border border-slate-100 p-5 text-center">
            <p className="text-3xl font-bold text-[var(--color-text)]">
              {typeof s.value === "number" ? s.value.toLocaleString() : s.value}
            </p>
            <p className="text-xs text-slate-400 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Listings by State */}
      {stats?.listings_by_state && Object.keys(stats.listings_by_state).length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <h3 className="text-sm font-bold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>Listings by State</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {Object.entries(stats.listings_by_state).map(([state, count]) => (
              <div key={state} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
                <Badge state={state} />
                <span className="text-sm font-bold text-[var(--color-text)] ml-2">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Revenue Summary */}
      {revenue && (
        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <h3 className="text-sm font-bold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>Revenue</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div><p className="text-2xl font-bold text-[var(--color-text)]">{revenue.subscription_tenant_count}</p><p className="text-xs text-slate-400">Active Subscriptions</p></div>
            <div><p className="text-2xl font-bold text-[var(--color-text)]">{revenue.credit_purchase_count}</p><p className="text-xs text-slate-400">Credit Purchases</p></div>
            <div><p className="text-2xl font-bold text-[var(--color-text)]">{revenue.total_credits_purchased.toLocaleString()}</p><p className="text-xs text-slate-400">Total Credits Sold</p></div>
            <div><p className="text-2xl font-bold text-[var(--color-text)]">{revenue.avg_credits_per_listing ?? "—"}</p><p className="text-xs text-slate-400">Avg Credits/Listing</p></div>
          </div>
        </div>
      )}

      {/* Global Credit Ledger */}
      {creditSummary && (
        <div className="bg-[#0B1120] rounded-2xl p-5 text-white">
          <h3 className="text-[10px] uppercase tracking-wider text-white/50 font-semibold mb-3">Global Credit Ledger</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div><p className="text-2xl font-bold">{creditSummary.credits_purchased_this_month}</p><p className="text-xs text-white/40">Purchased (month)</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.credits_used_this_month}</p><p className="text-xs text-white/40">Used (month)</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.credits_adjusted_this_month}</p><p className="text-xs text-white/40">Adjusted (month)</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.tenant_count_with_credits}</p><p className="text-xs text-white/40">Tenants w/ Credits</p></div>
          </div>
        </div>
      )}

      {/* Recent Events */}
      {events.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <h3 className="text-sm font-bold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>Recent Events</h3>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {events.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-xs py-1.5 border-b border-slate-50 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-slate-400">{new Date(e.created_at).toLocaleTimeString()}</span>
                  <span className="font-medium text-[var(--color-text)]">{e.event_type}</span>
                </div>
                {e.listing_id && <span className="text-slate-400 font-mono truncate max-w-[120px]">{e.listing_id.slice(0, 8)}…</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Tenants
// ═══════════════════════════════════════════════════════════════════════════
function TenantsTab() {
  const [tenants, setTenants] = useState<AdminTenantResponse[]>([]);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "plan" | "credit_balance">("name");
  const [selected, setSelected] = useState<string | null>(null);
  const [tenantCredits, setTenantCredits] = useState<TenantCreditsResponse | null>(null);
  const [tenantUsers, setTenantUsers] = useState<AdminUserItem[]>([]);

  // Adjust form
  const [adjustAmount, setAdjustAmount] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjustLoading, setAdjustLoading] = useState(false);
  const [adjustError, setAdjustError] = useState("");

  // Edit form
  const [editName, setEditName] = useState("");
  const [editPlan, setEditPlan] = useState("");
  const [editWebhook, setEditWebhook] = useState("");

  useEffect(() => { apiClient.adminTenants().then(setTenants).catch(console.error); }, []);

  const sorted = useMemo(() => [...tenants]
    .filter((t) => !search || t.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === "credit_balance") return (b.credit_balance ?? 0) - (a.credit_balance ?? 0);
      if (sortBy === "plan") return a.plan.localeCompare(b.plan);
      return a.name.localeCompare(b.name);
    }), [tenants, search, sortBy]);

  const selectedData = tenants.find((t) => t.id === selected);

  function handleSelect(id: string) {
    setSelected(id);
    setAdjustError("");
    const t = tenants.find((x) => x.id === id);
    if (t) { setEditName(t.name); setEditPlan(t.plan); setEditWebhook(t.webhook_url ?? ""); }
    apiClient.adminTenantCredits(id).then(setTenantCredits).catch(console.error);
    apiClient.adminAllUsers({ tenant_id: id }).then(setTenantUsers).catch(console.error);
  }

  async function handleAdjust() {
    if (!selected || !adjustAmount) return;
    setAdjustLoading(true);
    setAdjustError("");
    try {
      await apiClient.adminAdjustCredits(selected, Number(adjustAmount), adjustReason);
      apiClient.adminTenantCredits(selected).then(setTenantCredits);
      apiClient.adminTenants().then(setTenants);
      setAdjustAmount("");
      setAdjustReason("");
    } catch (err: any) {
      setAdjustError(err.message || "Adjustment failed");
    } finally {
      setAdjustLoading(false);
    }
  }

  async function handleUpdateTenant() {
    if (!selected) return;
    try {
      await apiClient.adminUpdateTenant(selected, { name: editName, plan: editPlan, webhook_url: editWebhook || undefined });
      apiClient.adminTenants().then(setTenants);
    } catch (err: any) {
      setAdjustError(err.message || "Update failed");
    }
  }

  async function handleRoleChange(userId: string, role: string) {
    await apiClient.adminChangeUserRole(userId, role);
    if (selected) apiClient.adminAllUsers({ tenant_id: selected }).then(setTenantUsers);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
      {/* Tenant Table */}
      <div className="lg:col-span-3">
        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>Tenant Roster</h2>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 w-32"
              />
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
                <th className="pb-2 text-right">Credits</th>
                <th className="pb-2 text-right">Listings</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t) => (
                <tr
                  key={t.id}
                  className={`border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition-colors ${selected === t.id ? "bg-[#F97316]/5" : ""}`}
                  onClick={() => handleSelect(t.id)}
                >
                  <td className="py-3 font-medium truncate max-w-[180px]">
                    {selected === t.id && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#F97316] mr-2" />}
                    {t.name}
                  </td>
                  <td className="py-3"><span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${planColor(t.plan)}`}>{t.plan}</span></td>
                  <td className="py-3 text-right font-mono">{t.credit_balance}</td>
                  <td className="py-3 text-right text-slate-400">{t.listing_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Panel */}
      <div className="lg:col-span-2 space-y-4">
        {selected && selectedData ? (
          <>
            {/* Tenant Info + Edit */}
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-500">
                  {selectedData.name.charAt(0)}
                </div>
                <div>
                  <p className="font-semibold text-[var(--color-text)]">{selectedData.name}</p>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wider">Since {new Date(selectedData.created_at).getFullYear()}</p>
                </div>
              </div>
              <div className="space-y-2 mb-3">
                <input className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2" value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Name" />
                <select className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2" value={editPlan} onChange={(e) => setEditPlan(e.target.value)}>
                  <option value="starter">Starter</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <input className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2" value={editWebhook} onChange={(e) => setEditWebhook(e.target.value)} placeholder="Webhook URL" />
                <button onClick={handleUpdateTenant} className="w-full text-xs font-semibold py-2 rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors">Save Changes</button>
              </div>
            </div>

            {/* Credits */}
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <div className="bg-[#F97316]/10 rounded-xl p-4 mb-4">
                <p className="text-[10px] uppercase tracking-wider text-[#F97316] font-semibold mb-1">Credit Balance</p>
                <p className="text-3xl font-bold text-[var(--color-text)]">{tenantCredits?.credit_balance?.toLocaleString() ?? "—"}</p>
              </div>
              <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">Credit Adjustment</p>
              <div className="flex gap-2 mb-2">
                <input type="number" className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2" value={adjustAmount} onChange={(e) => setAdjustAmount(e.target.value)} placeholder="Amount (+/-)" />
                <input className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2" value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)} placeholder="Reason" />
              </div>
              <button onClick={handleAdjust} disabled={adjustLoading} className="w-full text-xs font-semibold py-2 rounded-lg bg-[#F97316] text-white hover:bg-[#ea580c] disabled:opacity-50 transition-colors">
                {adjustLoading ? "Applying…" : "Apply Adjustment"}
              </button>
              {adjustError && <p className="text-xs text-red-500 mt-2">{adjustError}</p>}

              {/* Recent Transactions */}
              {tenantCredits?.transactions && tenantCredits.transactions.length > 0 && (
                <div className="mt-4 space-y-1 max-h-40 overflow-y-auto">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Recent Transactions</p>
                  {tenantCredits.transactions.slice(0, 10).map((tx) => (
                    <div key={tx.id} className="flex justify-between text-xs py-1 border-b border-slate-50">
                      <span className="text-slate-500">{tx.description || tx.transaction_type}</span>
                      <span className={tx.amount > 0 ? "text-green-600 font-semibold" : "text-red-500 font-semibold"}>
                        {tx.amount > 0 ? "+" : ""}{tx.amount}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Users */}
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-3">Users ({tenantUsers.length})</p>
              <div className="space-y-2">
                {tenantUsers.map((u) => (
                  <div key={u.id} className="flex items-center justify-between text-xs">
                    <div>
                      <p className="font-medium text-[var(--color-text)]">{u.name || u.email}</p>
                      <p className="text-slate-400">{u.email}</p>
                    </div>
                    <select
                      className="text-[10px] border border-slate-200 rounded px-2 py-1"
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                      <option value="superadmin">Superadmin</option>
                    </select>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-100 p-8 text-center">
            <p className="text-sm text-slate-400">Select a tenant to view details</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Listings
// ═══════════════════════════════════════════════════════════════════════════
function ListingsTab() {
  const [listings, setListings] = useState<AdminListingItem[]>([]);
  const [stateFilter, setStateFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 25;

  useEffect(() => {
    const params: Record<string, string | number> = { limit, offset };
    if (stateFilter) params.state = stateFilter;
    if (searchFilter) params.search = searchFilter;
    apiClient.adminListings(params as any).then(setListings).catch(console.error);
  }, [stateFilter, searchFilter, offset]);

  async function handleRetry(id: string) {
    await apiClient.adminRetryListing(id);
    apiClient.adminListings({ limit, offset, state: stateFilter || undefined, search: searchFilter || undefined } as any).then(setListings);
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white"
          value={stateFilter}
          onChange={(e) => { setStateFilter(e.target.value); setOffset(0); }}
        >
          <option value="">All States</option>
          {["new", "uploading", "analyzing", "awaiting_review", "in_review", "approved", "exporting", "delivered", "failed", "pipeline_timeout", "cancelled"].map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search address…"
          value={searchFilter}
          onChange={(e) => { setSearchFilter(e.target.value); setOffset(0); }}
          className="text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white w-48"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold border-b border-slate-100 bg-slate-50">
              <th className="px-4 py-3 text-left">Address</th>
              <th className="px-4 py-3 text-left">Tenant</th>
              <th className="px-4 py-3 text-left">State</th>
              <th className="px-4 py-3 text-right">Cost</th>
              <th className="px-4 py-3 text-right">Updated</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((l) => (
              <tr key={l.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-4 py-3 font-medium truncate max-w-[200px]">
                  <Link href={`/listings/${l.id}`} className="text-[#F97316] hover:underline">
                    {l.address?.street || "—"}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{l.tenant_name}</td>
                <td className="px-4 py-3"><Badge state={l.state} /></td>
                <td className="px-4 py-3 text-right font-mono text-xs">{l.credit_cost ?? "—"}</td>
                <td className="px-4 py-3 text-right text-xs text-slate-400">{new Date(l.updated_at).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right flex gap-2 justify-end">
                  {["awaiting_review", "in_review"].includes(l.state) && (
                    <Link
                      href={`/listings/${l.id}`}
                      className="text-[10px] font-semibold px-3 py-1 rounded-full bg-[#F97316] text-white hover:bg-[#ea580c]"
                    >
                      Review
                    </Link>
                  )}
                  {["failed", "pipeline_timeout"].includes(l.state) && (
                    <button
                      onClick={() => handleRetry(l.id)}
                      className="text-[10px] font-semibold px-3 py-1 rounded-full bg-[#F97316] text-white hover:bg-[#ea580c]"
                    >
                      Retry
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-400">No listings found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="text-xs px-4 py-2 rounded-lg bg-slate-100 disabled:opacity-30"
        >
          ← Previous
        </button>
        <span className="text-xs text-slate-400">Showing {offset + 1}–{offset + listings.length}</span>
        <button
          onClick={() => setOffset(offset + limit)}
          disabled={listings.length < limit}
          className="text-xs px-4 py-2 rounded-lg bg-slate-100 disabled:opacity-30"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Credits
// ═══════════════════════════════════════════════════════════════════════════
function CreditsTab() {
  const [tenants, setTenants] = useState<AdminTenantResponse[]>([]);
  const [creditSummary, setCreditSummary] = useState<CreditSummaryResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [tenantCredits, setTenantCredits] = useState<TenantCreditsResponse | null>(null);
  const [adjustAmount, setAdjustAmount] = useState("");
  const [adjustReason, setAdjustReason] = useState("");

  useEffect(() => {
    apiClient.adminTenants().then(setTenants).catch(console.error);
    apiClient.adminCreditsSummary().then(setCreditSummary).catch(console.error);
  }, []);

  function handleSelect(id: string) {
    setSelected(id);
    apiClient.adminTenantCredits(id).then(setTenantCredits).catch(console.error);
  }

  async function handleAdjust() {
    if (!selected || !adjustAmount) return;
    await apiClient.adminAdjustCredits(selected, Number(adjustAmount), adjustReason);
    apiClient.adminTenantCredits(selected).then(setTenantCredits);
    apiClient.adminTenants().then(setTenants);
    setAdjustAmount("");
    setAdjustReason("");
  }

  const sorted = useMemo(() => [...tenants].sort((a, b) => (b.credit_balance ?? 0) - (a.credit_balance ?? 0)), [tenants]);

  return (
    <div className="space-y-6">
      {/* Global Ledger */}
      {creditSummary && (
        <div className="bg-[#0B1120] rounded-2xl p-5 text-white">
          <h3 className="text-[10px] uppercase tracking-wider text-white/50 font-semibold mb-3">Global Credit Ledger</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div><p className="text-2xl font-bold">{creditSummary.credits_purchased_this_month}</p><p className="text-xs text-white/40">Purchased</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.credits_used_this_month}</p><p className="text-xs text-white/40">Used</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.credits_adjusted_this_month}</p><p className="text-xs text-white/40">Adjusted</p></div>
            <div><p className="text-2xl font-bold">{creditSummary.tenant_count_with_credits}</p><p className="text-xs text-white/40">Active</p></div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tenant Credit Table */}
        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <h3 className="text-sm font-bold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>Tenant Balances</h3>
          <div className="space-y-1 max-h-80 overflow-y-auto">
            {sorted.map((t) => (
              <div
                key={t.id}
                className={`flex justify-between items-center px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-50 ${selected === t.id ? "bg-[#F97316]/5" : ""}`}
                onClick={() => handleSelect(t.id)}
              >
                <span className="text-sm font-medium truncate max-w-[200px]">{t.name}</span>
                <span className="text-sm font-mono font-bold">{t.credit_balance}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Adjustment + History */}
        <div className="space-y-4">
          {selected && tenantCredits ? (
            <>
              <div className="bg-white rounded-2xl border border-slate-100 p-5">
                <p className="text-2xl font-bold text-[var(--color-text)] mb-3">Balance: {tenantCredits.credit_balance}</p>
                <div className="flex gap-2 mb-2">
                  <input type="number" className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2" value={adjustAmount} onChange={(e) => setAdjustAmount(e.target.value)} placeholder="+/- amount" />
                  <input className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2" value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)} placeholder="Reason" />
                </div>
                <button onClick={handleAdjust} className="w-full text-xs font-semibold py-2 rounded-lg bg-[#F97316] text-white hover:bg-[#ea580c]">Apply</button>
              </div>
              {tenantCredits.transactions.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-100 p-5 max-h-60 overflow-y-auto">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">Transaction History</p>
                  {tenantCredits.transactions.map((tx) => (
                    <div key={tx.id} className="flex justify-between text-xs py-1.5 border-b border-slate-50">
                      <div>
                        <span className="text-slate-500">{tx.description || tx.transaction_type}</span>
                        <span className="text-slate-300 ml-2">{new Date(tx.created_at).toLocaleDateString()}</span>
                      </div>
                      <span className={tx.amount > 0 ? "text-green-600 font-semibold" : "text-red-500 font-semibold"}>
                        {tx.amount > 0 ? "+" : ""}{tx.amount}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 p-8 text-center">
              <p className="text-sm text-slate-400">Select a tenant to manage credits</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Audit Log
// ═══════════════════════════════════════════════════════════════════════════
function AuditTab() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [actionFilter, setActionFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const limit = 30;

  useEffect(() => {
    setLoading(true);
    apiClient.adminAuditLog({
      action: actionFilter || undefined,
      resource_type: resourceFilter || undefined,
      limit,
    }).then(setLogs).catch(console.error).finally(() => setLoading(false));
  }, [actionFilter, resourceFilter]);

  async function loadMore() {
    setLoading(true);
    try {
      const more = await apiClient.adminAuditLog({
        action: actionFilter || undefined,
        resource_type: resourceFilter || undefined,
        limit,
        offset: logs.length,
      });
      setLogs((prev) => [...prev, ...more]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select className="text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
          <option value="">All Actions</option>
          {["update", "adjust_credits", "invite_user", "change_role", "update_listing", "retry_listing"].map((a) => (
            <option key={a} value={a}>{a.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select className="text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white" value={resourceFilter} onChange={(e) => setResourceFilter(e.target.value)}>
          <option value="">All Resources</option>
          {["tenant", "user", "listing", "credit"].map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* Log Table */}
      <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold border-b border-slate-100 bg-slate-50">
              <th className="px-4 py-3 text-left">Time</th>
              <th className="px-4 py-3 text-left">Action</th>
              <th className="px-4 py-3 text-left">Resource</th>
              <th className="px-4 py-3 text-left">Resource ID</th>
              <th className="px-4 py-3 text-left">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 font-medium">{log.action}</td>
                <td className="px-4 py-3 text-xs"><span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600">{log.resource_type}</span></td>
                <td className="px-4 py-3 text-xs font-mono text-slate-400 truncate max-w-[100px]">{log.resource_id?.slice(0, 8) ?? "—"}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                    className="text-[10px] text-[#F97316] font-semibold hover:underline"
                  >
                    {expanded === log.id ? "Hide" : "View"}
                  </button>
                  {expanded === log.id && (
                    <pre className="mt-2 text-[10px] bg-slate-50 rounded-lg p-2 max-w-xs overflow-x-auto">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  )}
                </td>
              </tr>
            ))}
            {logs.length === 0 && !loading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-400">No audit logs found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Load More */}
      {logs.length >= limit && (
        <div className="text-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="text-xs px-6 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load More"}
          </button>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: Support
// ═══════════════════════════════════════════════════════════════════════════

function SupportTab() {
  const [stats, setStats] = useState<{ open_count: number; in_progress_count: number; resolved_today: number; avg_response_hours: number | null } | null>(null);
  const [tickets, setTickets] = useState<Array<{ id: string; subject: string; category: string; priority: string; status: string; created_at: string; updated_at: string; user_email?: string; chat_session_id?: string; resolution_note?: string }>>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ id: string; subject: string; status: string; category: string; priority: string; resolution_note?: string; messages: Array<{ id: string; user_id: string; content: string; is_admin_reply: boolean; created_at: string; user_name?: string; user_email?: string; chat_transcript?: Array<{ role: string; content: string }> }> } | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [reply, setReply] = useState("");
  const [resolution, setResolution] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.adminSupportStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => { fetchTickets(); }, [statusFilter]);

  async function fetchTickets() {
    setLoading(true);
    try {
      const res = await apiClient.adminSupportTickets({ status: statusFilter === "all" ? undefined : statusFilter, limit: 50 });
      setTickets(res.items);
    } catch { /* silently handle */ } finally { setLoading(false); }
  }

  async function selectTicket(id: string) {
    setSelectedId(id);
    try {
      const d = await apiClient.adminSupportTicketDetail(id);
      setDetail(d);
      setResolution(d.resolution_note || "");
    } catch { /* silently handle */ }
  }

  async function handleReply() {
    if (!reply.trim() || !selectedId) return;
    try { await apiClient.adminReplyToTicket(selectedId, reply); setReply(""); selectTicket(selectedId); } catch { /* silently handle */ }
  }

  async function handleStatusChange(newStatus: string) {
    if (!selectedId) return;
    const updates: { status?: string; resolution_note?: string } = { status: newStatus };
    if (newStatus === "resolved" && resolution.trim()) updates.resolution_note = resolution;
    try { await apiClient.adminUpdateTicket(selectedId, updates); fetchTickets(); selectTicket(selectedId); } catch { /* silently handle */ }
  }

  const sc: Record<string, string> = { open: "bg-orange-100 text-orange-700", in_progress: "bg-blue-100 text-blue-700", resolved: "bg-green-100 text-green-700", closed: "bg-slate-100 text-slate-500" };

  return (
    <div>
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Open", value: stats.open_count, color: "text-orange-500" },
            { label: "In Progress", value: stats.in_progress_count, color: "text-blue-500" },
            { label: "Resolved Today", value: stats.resolved_today, color: "text-green-500" },
            { label: "Avg Response", value: stats.avg_response_hours != null ? `${stats.avg_response_hours}h` : "—", color: "text-[var(--color-text)]" },
          ].map((s) => (
            <div key={s.label} className="p-4 rounded-xl border border-[var(--color-card-border)] bg-[var(--color-surface)]">
              <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-2 mb-4">
        {["all", "open", "in_progress", "resolved", "closed"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${statusFilter === s ? "bg-[#F97316] text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}>
            {s === "all" ? "All" : s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-6">
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {loading ? <div className="text-center py-8 text-[var(--color-text-secondary)] text-sm">Loading...</div>
          : tickets.length === 0 ? <div className="text-center py-8 text-[var(--color-text-secondary)] text-sm">No tickets</div>
          : tickets.map((t) => (
            <div key={t.id} onClick={() => selectTicket(t.id)}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${selectedId === t.id ? "border-[#F97316]/40 bg-orange-50/30" : "border-[var(--color-card-border)] bg-[var(--color-surface)]"}`}>
              <p className="text-sm font-medium text-[var(--color-text)] truncate">{t.subject}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${sc[t.status] || sc.open}`}>{t.status.replace(/_/g, " ")}</span>
                <span className="text-[10px] text-[var(--color-text-secondary)]">{t.user_email}</span>
                {t.chat_session_id && <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">AI</span>}
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] min-h-[400px]">
          {!detail ? <div className="flex items-center justify-center h-full text-sm text-[var(--color-text-secondary)]">Select a ticket</div> : (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-[var(--color-card-border)]">
                <h3 className="text-base font-semibold text-[var(--color-text)]">{detail.subject}</h3>
                <div className="flex items-center gap-2 mt-2">
                  <select value={detail.status} onChange={(e) => handleStatusChange(e.target.value)}
                    className="px-2 py-1 rounded text-xs font-semibold border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)]">
                    <option value="open">Open</option><option value="in_progress">In Progress</option><option value="resolved">Resolved</option><option value="closed">Closed</option>
                  </select>
                  <span className="text-xs text-[var(--color-text-secondary)]">{detail.category} / {detail.priority}</span>
                </div>
                {(detail.status === "resolved" || detail.status === "closed") && (
                  <input type="text" value={resolution} onChange={(e) => setResolution(e.target.value)} placeholder="Resolution note..."
                    onBlur={() => { if (resolution !== (detail.resolution_note || "")) apiClient.adminUpdateTicket(detail.id, { resolution_note: resolution }); }}
                    className="w-full mt-2 px-2 py-1 rounded text-xs border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)]" />
                )}
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[350px]">
                {detail.messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.is_admin_reply ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${msg.is_admin_reply ? "bg-blue-50 dark:bg-blue-900/20 rounded-br-md" : "bg-[var(--color-bg)] border border-[var(--color-card-border)] rounded-bl-md"}`}>
                      <p className="text-[10px] font-semibold text-[var(--color-text-secondary)] mb-1">{msg.is_admin_reply ? "Admin" : msg.user_name || msg.user_email || "User"} — {new Date(msg.created_at).toLocaleString()}</p>
                      <p className="whitespace-pre-wrap text-[var(--color-text)]">{msg.content}</p>
                      {msg.chat_transcript && msg.chat_transcript.length > 0 && (
                        <details className="mt-2 pt-2 border-t border-[var(--color-card-border)]">
                          <summary className="text-[10px] text-blue-600 cursor-pointer font-semibold">AI Chat Transcript ({msg.chat_transcript.length} messages)</summary>
                          <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                            {msg.chat_transcript.map((m, i) => (
                              <p key={i} className="text-[11px] text-[var(--color-text-secondary)]"><span className="font-semibold">{m.role === "user" ? "User" : "AI"}:</span> {m.content.slice(0, 300)}{m.content.length > 300 ? "..." : ""}</p>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t border-[var(--color-card-border)]">
                <div className="flex gap-2">
                  <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} placeholder="Admin reply..."
                    className="flex-1 px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm resize-none" />
                  <button onClick={handleReply} disabled={!reply.trim()}
                    className="px-4 py-2 rounded-lg text-sm font-semibold text-white self-end disabled:opacity-50" style={{ background: "linear-gradient(135deg, #F97316, #FB923C)" }}>Reply</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
