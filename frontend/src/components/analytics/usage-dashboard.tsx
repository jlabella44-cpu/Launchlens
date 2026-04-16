"use client";

import { useEffect, useState } from "react";

interface UsageStats {
  timestamp: string;
  active_tenants: number;
  listings_today: number;
  active_pipelines: number;
  completed_today: number;
  total_credits_outstanding: number;
  by_state: Record<string, number>;
}

function Stat({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-4">
      <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-[var(--color-text)]">{value.toLocaleString()}</p>
      {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function UsageDashboard() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/v1";
    const es = new EventSource(`${apiBase}/admin/usage-stream`, { withCredentials: true });

    es.addEventListener("usage", (e) => {
      try {
        setStats(JSON.parse((e as MessageEvent).data));
        setConnected(true);
        setError(false);
      } catch {
        /* ignore parse errors */
      }
    });

    es.onerror = () => {
      setConnected(false);
      setError(true);
    };

    return () => es.close();
  }, []);

  if (error) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
        Usage stream unavailable
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-100 p-4 h-20 animate-pulse" />
        ))}
      </div>
    );
  }

  const updatedAt = new Date(stats.timestamp).toLocaleTimeString();

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[var(--color-text)]">Live Platform Usage</h3>
        <span className={`text-[10px] flex items-center gap-1 ${connected ? "text-green-500" : "text-slate-400"}`}>
          <span className={`w-1.5 h-1.5 rounded-full inline-block ${connected ? "bg-green-500 animate-pulse" : "bg-slate-300"}`} />
          {connected ? `Updated ${updatedAt}` : "Reconnecting…"}
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Active Tenants" value={stats.active_tenants} />
        <Stat label="Listings Today" value={stats.listings_today} />
        <Stat label="Active Pipelines" value={stats.active_pipelines} />
        <Stat label="Completed Today" value={stats.completed_today} />
      </div>
      <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
        <Stat
          label="Credits Outstanding"
          value={stats.total_credits_outstanding}
          sub="across all tenants"
        />
        {Object.entries(stats.by_state).slice(0, 5).map(([state, count]) => (
          <Stat key={state} label={state.replace(/_/g, " ")} value={count} sub="listings" />
        ))}
      </div>
    </div>
  );
}
