"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import type { TeamMemberResponse, InviteTeamMemberRequest, BlanketGrantResponse } from "@/lib/types";

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
  const { toast } = useToast();
  const [members, setMembers] = useState<TeamMemberResponse[]>([]);
  const [myProfile, setMyProfile] = useState<TeamMemberResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteForm, setInviteForm] = useState<InviteTeamMemberRequest>({
    email: "",
    name: "",
    role: "agent",
  });

  // Remove-member confirmation modal state
  const [removeTarget, setRemoveTarget] = useState<TeamMemberResponse | null>(null);
  const [removing, setRemoving] = useState(false);

  const [blanketGrants, setBlanketGrants] = useState<Record<string, BlanketGrantResponse | null>>({});

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

      // Fetch blanket grants for each member (admin only)
      if (profile.role === "admin" || profile.role === "superadmin") {
        const grantsMap: Record<string, BlanketGrantResponse | null> = {};
        await Promise.all(
          memberList.map(async (m) => {
            try {
              const grants = await apiClient.getBlanketGrants(m.id);
              grantsMap[m.id] = grants.length > 0 ? grants[0] : null;
            } catch {
              grantsMap[m.id] = null;
            }
          })
        );
        setBlanketGrants(grantsMap);
      }
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
    const email = inviteForm.email.trim().toLowerCase();
    try {
      await apiClient.inviteTeamMember({
        ...inviteForm,
        email,
      });
      setShowInvite(false);
      setInviteForm({ email: "", name: "", role: "agent" });
      toast(`Invitation sent to ${email}`, "success");
      await fetchData();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to invite member", "error");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(memberId: string, newRole: string) {
    try {
      await apiClient.updateTeamMemberRole(memberId, newRole);
      await fetchData();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to update role", "error");
    }
  }

  async function handleListingAccessChange(memberId: string, value: string) {
    const existingGrant = blanketGrants[memberId];
    try {
      // Revoke existing grant if any
      if (existingGrant) {
        await apiClient.revokeBlanketGrant(memberId, existingGrant.id);
      }
      // Create new grant if not "none"
      if (value === "read" || value === "write") {
        const newGrant = await apiClient.createBlanketGrant(memberId, value);
        setBlanketGrants((prev) => ({ ...prev, [memberId]: newGrant }));
      } else {
        setBlanketGrants((prev) => ({ ...prev, [memberId]: null }));
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to update listing access", "error");
      await fetchData();
    }
  }

  async function confirmRemove() {
    if (!removeTarget) return;
    setRemoving(true);
    try {
      await apiClient.removeTeamMember(removeTarget.id);
      toast("Member removed", "success");
      setRemoveTarget(null);
      await fetchData();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to remove member", "error");
    } finally {
      setRemoving(false);
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
                  className="text-lg font-bold text-[var(--color-text)] mb-1"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Invite New Member
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mb-4">
                  We&apos;ll email them a link to set their own password. No need
                  to share credentials.
                </p>
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
              <div className="hidden sm:grid grid-cols-[1fr_1fr_140px_150px_120px_80px] gap-4 px-6 py-3 border-b border-[var(--color-card-border)] text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">
                <span>Member</span>
                <span>Email</span>
                <span>Role</span>
                <span>Listing Access</span>
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
                    className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_140px_150px_120px_80px] gap-2 sm:gap-4 items-center px-6 py-4 border-b border-[var(--color-card-border)] last:border-b-0 hover:bg-[var(--color-bg)] transition-colors"
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
                          {member.pending_invite && (
                            <span
                              className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wider bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                              title="This user has not yet accepted their invitation"
                            >
                              Pending
                            </span>
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

                    {/* Listing Access */}
                    <div>
                      {isAdmin && !isSelf ? (
                        <select
                          value={blanketGrants[member.id]?.permission || "none"}
                          onChange={(e) => handleListingAccessChange(member.id, e.target.value)}
                          className="px-2.5 py-1 rounded-md text-xs font-semibold border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[#F97316] cursor-pointer"
                        >
                          <option value="none">Own listings only</option>
                          <option value="read">Read all listings</option>
                          <option value="write">Read &amp; write all</option>
                        </select>
                      ) : (
                        <span className="inline-block px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-500">
                          {isSelf
                            ? "Full access"
                            : blanketGrants[member.id]?.permission === "write"
                              ? "Read & write all"
                              : blanketGrants[member.id]?.permission === "read"
                                ? "Read all listings"
                                : "Own listings only"}
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
                          onClick={() => setRemoveTarget(member)}
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

      {/* Remove-member confirmation modal */}
      <AnimatePresence>
        {removeTarget && (
          <motion.div
            key="remove-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="remove-member-title"
            onClick={() => !removing && setRemoveTarget(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] p-6 shadow-2xl"
            >
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
                  <svg
                    className="w-5 h-5 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <h3
                    id="remove-member-title"
                    className="text-base font-bold text-[var(--color-text)]"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    Remove team member
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                    Are you sure you want to remove{" "}
                    <span className="font-semibold text-[var(--color-text)]">
                      {removeTarget.name || removeTarget.email}
                    </span>
                    ? They&apos;ll immediately lose access to this workspace.
                    This cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-5">
                <button
                  type="button"
                  onClick={() => setRemoveTarget(null)}
                  disabled={removing}
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-[var(--color-text-secondary)] border border-[var(--color-card-border)] hover:text-[var(--color-text)] transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmRemove}
                  disabled={removing}
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-50"
                >
                  {removing ? "Removing..." : "Remove"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
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
