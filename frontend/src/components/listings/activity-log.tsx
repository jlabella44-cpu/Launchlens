"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
import type { AuditLogEntryResponse } from "@/lib/types";

interface ActivityLogProps {
  listingId: string;
}

const ACTION_LABELS: Record<string, (details: Record<string, unknown>) => string> = {
  share: (d) => `Shared listing with ${d.grantee_email ?? "a user"}`,
  unshare: (d) => `Revoked access for ${d.grantee_email ?? "a user"}`,
  update_permission: () => "Changed permission level",
  edit_description: () => "Edited listing description",
  upload_photo: () => "Uploaded photos",
  delete_photo: () => "Deleted a photo",
  export: () => "Exported listing package",
  publish_mls: () => "Published to MLS",
};

function describeAction(action: string, details: Record<string, unknown>): string {
  const formatter = ACTION_LABELS[action];
  if (formatter) return formatter(details);
  return action.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function relativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay === 1) {
    return `Yesterday at ${date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  }
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

function userInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 animate-pulse">
      <div className="w-8 h-8 rounded-full bg-slate-200 flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-40 bg-slate-200 rounded" />
        <div className="h-3 w-24 bg-slate-100 rounded" />
      </div>
    </div>
  );
}

export function ActivityLog({ listingId }: ActivityLogProps) {
  const [entries, setEntries] = useState<AuditLogEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function fetch() {
      try {
        const data = await apiClient.getListingAuditLog(listingId);
        if (!cancelled) setEntries(data);
      } catch {
        // Silently handle 404 (endpoint not deployed yet) — show empty state
        if (!cancelled) setEntries([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [listingId]);

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5">
      <h3
        className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Activity Log
      </h3>

      {loading && (
        <div className="space-y-5">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      )}

      {!loading && error && (
        <p className="text-sm text-red-500 py-4 text-center">{error}</p>
      )}

      {!loading && !error && entries.length === 0 && (
        <p className="text-sm text-slate-400 py-6 text-center">
          No activity recorded yet.
        </p>
      )}

      {!loading && !error && entries.length > 0 && (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[15px] top-4 bottom-4 w-px bg-slate-100" />

          <ul className="space-y-5">
            {entries.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 relative">
                {/* Avatar */}
                <div
                  className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold text-white relative z-10"
                  style={{ backgroundColor: "var(--color-primary, #F97316)" }}
                >
                  {userInitials(entry.user_name, entry.user_email)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--color-text)]">
                    <span className="font-medium">
                      {entry.user_name || entry.user_email}
                    </span>{" "}
                    <span className="text-slate-500">
                      {describeAction(entry.action, entry.details)}
                    </span>
                  </p>

                  {/* Extra detail for permission changes */}
                  {entry.action === "share" && entry.details.permission != null ? (
                    <p className="text-xs text-slate-400 mt-0.5">
                      Permission: {String(entry.details.permission)}
                    </p>
                  ) : null}

                  <p className="text-[11px] text-slate-300 mt-0.5">
                    {relativeTime(entry.created_at)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
