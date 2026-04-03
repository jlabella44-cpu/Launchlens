"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

const STATE_COLORS: Record<string, string> = {
  new: "#94a3b8",
  uploading: "#60a5fa",
  analyzing: "#a78bfa",
  awaiting_review: "#fbbf24",
  in_review: "#f97316",
  approved: "#34d399",
  delivered: "#10b981",
  failed: "#ef4444",
  cancelled: "#6b7280",
  exporting: "#3b82f6",
  demo: "#d1d5db",
  pipeline_timeout: "#dc2626",
};

const STATE_LABELS: Record<string, string> = {
  new: "New",
  uploading: "Uploading",
  analyzing: "Analyzing",
  awaiting_review: "Awaiting Review",
  in_review: "In Review",
  approved: "Approved",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
  exporting: "Exporting",
  demo: "Demo",
  pipeline_timeout: "Timeout",
};

export function StateBreakdown({ byState }: { byState: Record<string, number> }) {
  const data = Object.entries(byState)
    .filter(([, count]) => count > 0)
    .map(([state, count]) => ({
      state,
      label: STATE_LABELS[state] || state,
      count,
      color: STATE_COLORS[state] || "#94a3b8",
    }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
        No listings yet
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          type="number"
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={100}
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="count" name="Listings" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell key={entry.state} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
