"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";
import type { ListingResponse, AssetResponse, PackageSelection } from "@/lib/types";

const REASON_CODES = [
  { value: "quality", label: "Quality Issues" },
  { value: "incomplete", label: "Incomplete Coverage" },
  { value: "non_compliant", label: "Non-Compliant" },
  { value: "other", label: "Other" },
] as const;

type ReasonCode = (typeof REASON_CODES)[number]["value"];

interface ExpandedData {
  assets: AssetResponse[];
  selections: PackageSelection[];
}

function ReviewQueue() {
  const { toast } = useToast();
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<Record<string, ExpandedData>>({});
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<ReasonCode>("quality");
  const [rejectDetail, setRejectDetail] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const prevCountRef = useRef(0);

  useEffect(() => { document.title = "Review Queue | ListingJet"; }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const data = await apiClient.getReviewQueue();
      setListings(data);
      if (prevCountRef.current > 0 && data.length > prevCountRef.current) {
        toast(`${data.length - prevCountRef.current} new listing(s) in queue`, "info");
      }
      prevCountRef.current = data.length;
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 30_000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const idx = listings.findIndex((l) => l.id === expandedId);
      if (e.key === "j" && idx < listings.length - 1) {
        setExpandedId(listings[idx + 1]?.id ?? null);
      } else if (e.key === "k" && idx > 0) {
        setExpandedId(listings[idx - 1]?.id ?? null);
      } else if (e.key === "a" && expandedId) {
        handleApprove(expandedId);
      } else if (e.key === "s" && expandedId) {
        setRejectingId(expandedId);
      } else if (e.key === " " && listings.length > 0) {
        e.preventDefault();
        setExpandedId((prev) => (prev ? null : listings[0]?.id ?? null));
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [listings, expandedId]);

  async function toggleExpand(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (!expandedData[id]) {
      try {
        const [assets, selections] = await Promise.all([
          apiClient.getAssets(id),
          apiClient.getPackage(id),
        ]);
        setExpandedData((prev) => ({ ...prev, [id]: { assets, selections } }));
      } catch {
        toast("Failed to load listing details", "error");
      }
    }
  }

  async function handleApprove(id: string) {
    setActionLoading(id);
    try {
      await apiClient.startReview(id);
      await apiClient.approveListing(id);
      setListings((prev) => prev.filter((l) => l.id !== id));
      toast("Listing approved", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to approve", "error");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(id: string) {
    setActionLoading(id);
    try {
      await apiClient.rejectListing(id, {
        reason: rejectReason,
        detail: rejectReason === "other" ? rejectDetail : undefined,
      });
      setListings((prev) => prev.filter((l) => l.id !== id));
      setRejectingId(null);
      setRejectDetail("");
      toast("Listing rejected", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to reject", "error");
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <h1
              className="text-3xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Review Queue
            </h1>
            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[#F97316] text-white text-xs font-bold">
              {listings.length}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Process pending listings for pre-flight altitude clearance
            </p>
            <div className="hidden sm:flex items-center gap-4">
              <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                j/k navigate · a approve · s reject · space toggle
              </span>
            </div>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-2xl bg-[var(--color-surface)] animate-pulse border border-[var(--color-card-border)]" />
            ))}
          </div>
        ) : listings.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <p className="text-lg text-[var(--color-text-secondary)]">
              No listings awaiting review. Queue refreshes every 30s.
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] mt-2 uppercase tracking-wider">Load More Flights</p>
          </motion.div>
        ) : (
          <div className="space-y-3">
            {/* Table Header */}
            <div className="flex items-center gap-4 px-5 py-2 text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">
              <div className="flex-1">Street Address</div>
              <div className="w-40">Date Submitted</div>
              <div className="w-36 text-center">Status</div>
              <div className="w-24 text-center">Actions</div>
            </div>

            {listings.map((listing) => {
              const addr = listing.address;
              const isExpanded = expandedId === listing.id;
              const data = expandedData[listing.id];

              return (
                <motion.div key={listing.id} layout>
                  <div className={`bg-[var(--color-surface)] rounded-2xl border transition-all ${
                    isExpanded ? "border-[#F97316]/30 shadow-md" : "border-[var(--color-card-border)]"
                  }`}>
                    {/* Row */}
                    <div
                      className="flex items-center gap-4 px-5 py-4 cursor-pointer"
                      onClick={() => toggleExpand(listing.id)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--color-text)] truncate">
                          {addr.street || "Untitled"}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)]">
                          {[addr.city, addr.state].filter(Boolean).join(", ")}
                        </p>
                      </div>
                      <div className="w-40 text-xs text-[var(--color-text-secondary)]">
                        {new Date(listing.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })},{" "}
                        {new Date(listing.created_at).toLocaleTimeString("en-US", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      <div className="w-36 flex justify-center">
                        <Badge state={listing.state} />
                      </div>
                      <div className="w-24 flex justify-center gap-2">
                        {/* Approve */}
                        <button
                          onClick={(e) => { e.stopPropagation(); handleApprove(listing.id); }}
                          disabled={actionLoading === listing.id}
                          className="w-8 h-8 rounded-full border border-green-200 flex items-center justify-center text-green-500 hover:bg-green-50 transition-colors disabled:opacity-50"
                          aria-label="Approve"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                        {/* Reject */}
                        <button
                          onClick={(e) => { e.stopPropagation(); setRejectingId(listing.id); }}
                          className="w-8 h-8 rounded-full border border-red-200 flex items-center justify-center text-red-500 hover:bg-red-50 transition-colors"
                          aria-label="Reject"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Expanded photo grid */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-5 pb-5 pt-2 border-t border-[var(--color-card-border)]">
                            {!data ? (
                              <div className="h-24 flex items-center justify-center">
                                <div className="w-5 h-5 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
                              </div>
                            ) : data.selections.length === 0 ? (
                              <p className="text-sm text-[var(--color-text-secondary)] text-center py-4">
                                No packaged photos yet.
                              </p>
                            ) : (
                              <>
                                <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 mb-4">
                                  {data.selections.map((sel) => (
                                    <div
                                      key={`${sel.asset_id}-${sel.position}`}
                                      className="aspect-square bg-gradient-to-br from-slate-100 to-slate-50 rounded-xl overflow-hidden flex items-center justify-center relative"
                                    >
                                      <svg className="w-5 h-5 text-slate-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                      </svg>
                                    </div>
                                  ))}
                                </div>

                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-6">
                                    <div>
                                      <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">AI Trust Score</p>
                                      <p className="text-lg font-bold text-[var(--color-text)]">
                                        {data.selections.length > 0
                                          ? (data.selections.reduce((s, sel) => s + sel.composite_score, 0) / data.selections.length).toFixed(1)
                                          : "—"}%
                                      </p>
                                    </div>
                                    <div>
                                      <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">Glamour Score</p>
                                      <p className="text-lg font-bold text-[var(--color-text)]">None</p>
                                    </div>
                                  </div>
                                  <Link href={`/listings/${listing.id}`}>
                                    <button className="px-4 py-2 rounded-full bg-[#0B1120] text-white text-xs font-semibold uppercase tracking-wider hover:bg-[#1a2744] transition-colors">
                                      View Full Asset
                                    </button>
                                  </Link>
                                </div>
                              </>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Reject panel */}
                    <AnimatePresence>
                      {rejectingId === listing.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="px-5 pb-5 pt-3 border-t border-red-100 space-y-3">
                            <p className="text-sm font-semibold text-red-600">Rejection Reason</p>
                            <div className="flex flex-wrap gap-2">
                              {REASON_CODES.map((rc) => (
                                <button
                                  key={rc.value}
                                  onClick={() => setRejectReason(rc.value)}
                                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors cursor-pointer ${
                                    rejectReason === rc.value
                                      ? "bg-red-50 border-red-300 text-red-700"
                                      : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-secondary)]"
                                  }`}
                                >
                                  {rc.label}
                                </button>
                              ))}
                            </div>
                            {rejectReason === "other" && (
                              <input
                                type="text"
                                value={rejectDetail}
                                onChange={(e) => setRejectDetail(e.target.value)}
                                placeholder="Describe the issue..."
                                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-red-300"
                              />
                            )}
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleReject(listing.id)}
                                disabled={actionLoading === listing.id}
                                className="px-4 py-2 rounded-full bg-red-600 text-white text-xs font-semibold disabled:opacity-50"
                              >
                                Confirm Reject
                              </button>
                              <button
                                onClick={() => { setRejectingId(null); setRejectDetail(""); }}
                                className="px-4 py-2 rounded-full border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)]"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              );
            })}

            {/* Load more */}
            <div className="text-center pt-4">
              <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">Load More Flights</span>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-[var(--color-card-border)] flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
          <span>ListingJet</span>
          <span>© {new Date().getFullYear()} ListingJet Command. All systems operational.</span>
          <div className="flex items-center gap-6">
            <span>Support</span>
            <span>Privacy</span>
            <span>Terms</span>
            <span>API Status</span>
          </div>
        </footer>
      </main>
    </>
  );
}

function AdminGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && user.role !== "admin" && user.role !== "superadmin") {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  if (loading || !user) return null;
  if (user.role !== "admin" && user.role !== "superadmin") return null;

  return <>{children}</>;
}

export default function ReviewPage() {
  return (
    <ProtectedRoute>
      <AdminGate>
        <ReviewQueue />
      </AdminGate>
    </ProtectedRoute>
  );
}
