"use client";

import { useState } from "react";

interface Mismatch {
  field: string;
  api_value: any;
  sources: Record<string, any>;
}

interface VerificationBadgeProps {
  status: "pending" | "verified" | "mismatches_found" | "partial" | "skipped";
  sourcesCount?: number;
  mismatches?: Mismatch[];
  onAcceptMismatch?: (field: string, value: any) => void;
  onKeepValue?: (field: string) => void;
}

export function VerificationBadge({
  status,
  sourcesCount = 0,
  mismatches = [],
  onAcceptMismatch,
  onKeepValue,
}: VerificationBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  if (status === "skipped" || status === "pending") {
    return null;
  }

  if (status === "verified") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        ✓ Verified against {sourcesCount} source{sourcesCount !== 1 ? "s" : ""}
      </span>
    );
  }

  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium bg-zinc-500/10 text-zinc-400 border border-zinc-700">
        Partially verified
      </span>
    );
  }

  if (status === "mismatches_found") {
    return (
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors cursor-pointer"
        >
          ⚠ {mismatches.length} mismatch{mismatches.length !== 1 ? "es" : ""} found
          <svg
            className={`w-3.5 h-3.5 ml-0.5 transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {expanded && mismatches.length > 0 && (
          <div className="rounded-lg border border-zinc-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-800 text-zinc-400 text-xs uppercase tracking-wider">
                  <th className="px-4 py-2.5 text-left font-medium">Field</th>
                  <th className="px-4 py-2.5 text-left font-medium">Your Value</th>
                  <th className="px-4 py-2.5 text-left font-medium">Public Records</th>
                  <th className="px-4 py-2.5 text-left font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-700">
                {mismatches.map((mismatch) => {
                  const publicValues = Object.values(mismatch.sources)
                    .filter((v) => v !== undefined && v !== null)
                    .join(", ");

                  return (
                    <tr key={mismatch.field} className="bg-zinc-900/50">
                      <td className="px-4 py-3 text-zinc-300 font-medium capitalize">
                        {mismatch.field.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-3 text-zinc-400">
                        {String(mismatch.api_value ?? "—")}
                      </td>
                      <td className="px-4 py-3 text-amber-400/80">
                        {publicValues || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onAcceptMismatch?.(mismatch.field, mismatch.api_value)}
                            className="rounded px-2.5 py-1 text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition-colors"
                          >
                            Accept
                          </button>
                          <button
                            type="button"
                            onClick={() => onKeepValue?.(mismatch.field)}
                            className="rounded px-2.5 py-1 text-xs font-medium bg-zinc-700/50 text-zinc-400 border border-zinc-600 hover:bg-zinc-700 transition-colors"
                          >
                            Keep
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return null;
}
