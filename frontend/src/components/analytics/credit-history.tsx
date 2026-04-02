"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { CreditDataPoint } from "@/lib/types";

export function CreditHistory({ data }: { data: CreditDataPoint[] }) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
        No credit activity yet
      </p>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
          tickLine={false}
        />
        <YAxis
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
          formatter={(value, name) => {
            const num = Number(value);
            if (name === "Balance") return [num, "Credits"];
            const sign = num >= 0 ? "+" : "";
            return [`${sign}${num}`, "Change"];
          }}
        />
        <Line
          type="stepAfter"
          dataKey="balance_after"
          stroke="var(--color-primary)"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Balance"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
