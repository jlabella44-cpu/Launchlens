"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Select } from "@/components/ui/select";
import apiClient from "@/lib/api-client";
import type { ListingPermissionResponse } from "@/lib/types";

const PERMISSION_OPTIONS = [
  { value: "read", label: "Read Only" },
  { value: "write", label: "Read & Write" },
  { value: "publish", label: "Publish to MLS" },
  { value: "billing", label: "Full (incl. Billing)" },
];

const PERMISSION_COLORS: Record<string, string> = {
  read: "bg-blue-100 text-blue-700",
  write: "bg-green-100 text-green-700",
  publish: "bg-purple-100 text-purple-700",
  billing: "bg-orange-100 text-orange-700",
};

interface SharePanelProps {
  listingId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function SharePanel({ listingId, isOpen, onClose }: SharePanelProps) {
  const [permissions, setPermissions] = useState<ListingPermissionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [permLevel, setPermLevel] = useState("read");
  const [sharing, setSharing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (isOpen) {
      loadPermissions();
    }
  }, [isOpen, listingId]);

  async function loadPermissions() {
    setLoading(true);
    try {
      const perms = await apiClient.getListingPermissions(listingId);
      setPermissions(perms);
    } catch {
      // silently fail — panel just shows empty
    } finally {
      setLoading(false);
    }
  }

  async function handleShare(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSharing(true);
    setError("");
    setSuccess("");
    try {
      await apiClient.shareListing(listingId, {
        email: email.trim(),
        permission: permLevel,
      });
      setEmail("");
      setPermLevel("read");
      setSuccess(`Shared with ${email.trim()}`);
      setTimeout(() => setSuccess(""), 3000);
      loadPermissions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to share listing";
      if (msg.toLowerCase().includes("plan") || msg.toLowerCase().includes("upgrade") || msg.toLowerCase().includes("enterprise")) {
        setError("Listing sharing requires a Pro plan (or Enterprise for cross-brokerage sharing). Upgrade your plan to unlock this feature.");
      } else {
        setError(msg);
      }
    } finally {
      setSharing(false);
    }
  }

  async function handleRevoke(permissionId: string) {
    if (!window.confirm("Revoke this person's access?")) return;
    try {
      await apiClient.revokeListingPermission(listingId, permissionId);
      setPermissions((prev) => prev.filter((p) => p.id !== permissionId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke access");
    }
  }

  async function handleUpdatePermission(permissionId: string, newLevel: string) {
    try {
      const updated = await apiClient.updateListingPermission(listingId, permissionId, {
        permission: newLevel,
      });
      setPermissions((prev) =>
        prev.map((p) => (p.id === permissionId ? { ...p, permission: updated.permission } : p))
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update permission");
    }
  }

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="fixed right-0 top-0 h-full w-full max-w-md bg-[var(--color-surface)] border-l border-[var(--color-card-border)] shadow-2xl z-50 flex flex-col"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-[var(--color-card-border)] flex items-center justify-between">
        <div>
          <h2
            className="text-lg font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Share Listing
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)]">
            Grant access to team members or co-listing agents
          </p>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-[var(--color-background)] text-[var(--color-text-secondary)] transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Invite Form */}
      <form onSubmit={handleShare} className="px-6 py-4 border-b border-[var(--color-card-border)]">
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
          Invite by Email
        </label>
        <div className="flex gap-2 mb-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="agent@brokerage.com"
            required
            className="flex-1 px-3 py-2 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all"
          />
        </div>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
              Permission
            </label>
            <Select
              value={permLevel}
              onChange={(e) => setPermLevel(e.target.value)}
              options={PERMISSION_OPTIONS}
            />
          </div>
          <button
            type="submit"
            disabled={sharing || !email.trim()}
            className="px-4 py-2 rounded-lg bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            {sharing ? (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
            Share
          </button>
        </div>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-2">{error}</p>
        )}
        {success && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-green-600 bg-green-50 rounded-lg px-3 py-2 mt-2"
          >
            {success}
          </motion.p>
        )}

        <p className="text-[10px] text-[var(--color-text-secondary)] mt-2">
          <svg className="w-3 h-3 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          MLS publishing by non-listing agents may violate MLS rules. Verify with your board.
        </p>
      </form>

      {/* Current Shares */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
          People with Access ({permissions.length})
        </p>

        {loading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-14 rounded-lg bg-[var(--color-background)] animate-pulse" />
            ))}
          </div>
        ) : permissions.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-10 h-10 mx-auto text-slate-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
            <p className="text-sm text-slate-400">No one else has access yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {permissions.map((perm) => (
              <div
                key={perm.id}
                className="flex items-center justify-between p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-card-border)]"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {/* Avatar initials */}
                  <div className="w-8 h-8 rounded-full bg-[#0F1B2D] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                    {(perm.grantee_name || perm.grantee_email).charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--color-text)] truncate">
                      {perm.grantee_name || perm.grantee_email}
                    </p>
                    {perm.grantee_name && (
                      <p className="text-[10px] text-[var(--color-text-secondary)] truncate">
                        {perm.grantee_email}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Permission badge / dropdown */}
                  <select
                    value={perm.permission}
                    onChange={(e) => handleUpdatePermission(perm.id, e.target.value)}
                    className={`text-[10px] font-bold uppercase tracking-wider rounded-full px-2 py-0.5 border-none cursor-pointer ${PERMISSION_COLORS[perm.permission] || "bg-slate-100 text-slate-700"}`}
                  >
                    {PERMISSION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>

                  {/* Revoke */}
                  <button
                    onClick={() => handleRevoke(perm.id)}
                    className="w-6 h-6 rounded-full flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                    title="Revoke access"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-[var(--color-card-border)] text-center">
        <p className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
          Enterprise feature — listing-level permissions
        </p>
      </div>
    </motion.div>
  );
}
