"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import apiClient from "@/lib/api-client";
import type { TeamMemberResponse, InviteTeamMemberRequest } from "@/lib/types";

const ROLE_COLORS: Record<string, { bg: string; text: string }> = {
  superadmin: { bg: "rgba(239, 68, 68, 0.15)", text: "#EF4444" },
  admin: { bg: "rgba(249, 115, 22, 0.15)", text: "#F97316" },
  operator: { bg: "rgba(59, 130, 246, 0.15)", text: "#3B82F6" },
  agent: { bg: "rgba(34, 197, 94, 0.15)", text: "#22C55E" },
  viewer: { bg: "rgba(156, 163, 175, 0.15)", text: "#9CA3AF" },
};

const ROLE_OPTIONS = ["agent", "operator", "admin", "viewer"];

function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function TeamManagement() {
  const [members, setMembers] = useState<TeamMemberResponse[]>([]);
  const [myProfile, setMyProfile] = useState<TeamMemberResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteForm, setInviteForm] = useState<InviteTeamMemberRequest>({
    email: "",
    password: "",
    name: "",
    role: "agent",
  });

  const isAdmin = myProfile?.role === "admin" || myProfile?.role === "superadmin";

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profile, memberList] = await Promise.all([
        apiClient.getMyProfile(),
        apiClient.getTeamMembers().catch(() => [] as TeamMemberResponse[]),
      ]);
      setMyProfile(profile);
      setMembers(memberList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load team data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    document.title = "Team | ListingJet";
    fetchData();
  }, [fetchData]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setInviting(true);
    try {
      await apiClient.inviteTeamMember({
        ...inviteForm,
        email: inviteForm.email.trim().toLowerCase(),
      });
      setShowInvite(false);
      setInviteForm({ email: "", password: "", name: "", role: "agent" });
      await fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to invite member");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(memberId: string, newRole: string) {
    try {
      await apiClient.updateTeamMemberRole(memberId, newRole);
      await fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update role");
    }
  }

  async function handleRemove(memberId: string, memberName: string | null) {
    const label = memberName || "this member";
    if (!window.confirm(`Remove ${label} from your team? This action cannot be undone.`)) return;
    try {
      await apiClient.removeTeamMember(memberId);
      await fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to remove member");
    }
  }

  /* Loading skeleton */
  if (loading) {
    return (
      <>
        <Nav />
        <main className="flex-1 max-w-[1200px] mx-auto w-full px-4 sm:px-6 py-8">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-16 rounded-xl bg-[var(--color-surface)] animate-pulse border border-[var(--color-card-border)]"
              />
            ))}
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-[1200px] mx-auto w-full px-4 sm:px-6 py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header */}
          <div className="mb-8 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-[#F97316]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span className="text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-secondary)] font-semibold">
                  Flight Crew
                </span>
              </div>
              <h1
                className="text-4xl font-bold text-[var(--color-text)]"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Team Management
              </h1>
              <p className="text-base text-[var(--color-text-secondary)] mt-2">
                Manage your crew members and their access levels.
              </p>
            </div>
            {isAdmin && (
              <button
                onClick={() => setShowInvite(!showInvite)}
                className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all"
                style={{
                  fontFamily: "var(--font-heading)",
                  background: "linear-gradient(135deg, #F97316, #FB923C)",
                }}
              >
                {showInvite ? "Cancel" : "+ Invite Member"}
              </button>
            )}
          </div>

          {/* Error state */}
          {error && (
            <div className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Invite form */}
          {showInvite && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="mb-6"
            >
              <form
                onSubmit={handleInvite}
                className="p-6 rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)]"
              >
                <h3
                  className="text-lg font-bold text-[var(--color-text)] mb-4"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Invite New Member
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">
                      Email *
                    </label>
                    <input
                      type="email"
                      required
                      value={inviteForm.email}
                      onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                      placeholder="crew@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">
                      Name
                    </label>
                    <input
                      type="text"
                      value={inviteForm.name || ""}
                      onChange={(e) => setInviteForm((f) => ({ ...f, name: e.target.value || undefined }))}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                      placeholder="Jane Doe"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">
                      Password *
                    </label>
                    <input
                      type="password"
                      required
                      value={inviteForm.password}
                      onChange={(e) => setInviteForm((f) => ({ ...f, password: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                      placeholder="Temporary password"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">
                      Role
                    </label>
                    <select
                      value={inviteForm.role || "agent"}
                      onChange={(e) => setInviteForm((f) => ({ ...f, role: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>
                          {r.charAt(0).toUpperCase() + r.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 mt-5">
                  <button
                    type="submit"
                    disabled={inviting}
                    className="px-5 py-2 rounded-lg text-sm font-semibold text-white transition-all disabled:opacity-50"
                    style={{
                      fontFamily: "var(--font-heading)",
                      background: "linear-gradient(135deg, #F97316, #FB923C)",
                    }}
                  >
                    {inviting ? "Inviting..." : "Send Invite"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowInvite(false)}
                    className="px-5 py-2 rounded-lg text-sm font-semibold text-[var(--color-text-secondary)] border border-[var(--color-card-border)] hover:text-[var(--color-text)] transition-colors"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {/* Empty state */}
          {members.length === 0 && !error && (
            <div className="text-center py-16 text-[var(--color-text-secondary)]">
              <svg className="w-12 h-12 mx-auto mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
                No team members yet
              </p>
              <p className="text-sm mt-1">Invite your first crew member to get started.</p>
            </div>
          )}

          {/* Member list */}
          {members.length > 0 && (
            <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] overflow-hidden">
              {/* Table header */}
              <div className="hidden sm:grid grid-cols-[1fr_1fr_140px_120px_80px] gap-4 px-6 py-3 border-b border-[var(--color-card-border)] text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">
                <span>Member</span>
                <span>Email</span>
                <span>Role</span>
                <span>Joined</span>
                <span />
              </div>

              {/* Rows */}
              {members.map((member) => {
                const colors = ROLE_COLORS[member.role] || ROLE_COLORS.viewer;
                const isSelf = member.id === myProfile?.id;

                return (
                  <div
                    key={member.id}
                    className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_140px_120px_80px] gap-2 sm:gap-4 items-center px-6 py-4 border-b border-[var(--color-card-border)] last:border-b-0 hover:bg-[var(--color-bg)] transition-colors"
                  >
                    {/* Name + avatar */}
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                        style={{ background: colors.bg, color: colors.text }}
                      >
                        {getInitials(member.name, member.email)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-[var(--color-text)] truncate">
                          {member.name || "Unnamed"}
                          {isSelf && (
                            <span className="ml-2 text-[10px] text-[var(--color-text-secondary)]">(you)</span>
                          )}
                        </p>
                      </div>
                    </div>

                    {/* Email */}
                    <p className="text-sm text-[var(--color-text-secondary)] truncate">
                      {member.email}
                    </p>

                    {/* Role */}
                    <div>
                      {isAdmin && !isSelf ? (
                        <select
                          value={member.role}
                          onChange={(e) => handleRoleChange(member.id, e.target.value)}
                          className="px-2.5 py-1 rounded-md text-xs font-semibold border-0 focus:outline-none focus:ring-1 focus:ring-[#F97316] cursor-pointer"
                          style={{
                            background: colors.bg,
                            color: colors.text,
                          }}
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r.charAt(0).toUpperCase() + r.slice(1)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className="inline-block px-2.5 py-1 rounded-md text-xs font-semibold"
                          style={{ background: colors.bg, color: colors.text }}
                        >
                          {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                        </span>
                      )}
                    </div>

                    {/* Joined */}
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      {formatDate(member.created_at)}
                    </p>

                    {/* Remove */}
                    <div className="flex justify-end">
                      {isAdmin && !isSelf && (
                        <button
                          onClick={() => handleRemove(member.id, member.name)}
                          className="p-1.5 rounded-md text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Remove member"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </motion.div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-[var(--color-card-border)] flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
          <span>ListingJet Command</span>
          <div className="flex gap-6">
            <span>Flight Manual</span>
            <span>Ground Control</span>
            <span>Hangar Support</span>
          </div>
        </footer>
      </main>
    </>
  );
}

export default function TeamPage() {
  return (
    <ProtectedRoute>
      <TeamManagement />
    </ProtectedRoute>
  );
}
