"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { useToast } from "@/components/ui/toast";
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

  const fetchQueue = useCallback(async () => {
    try {
      const data = await apiClient.getReviewQueue();
      setListings(data);
      if (prevCountRef.current > 0 && data.length > prevCountRef.current) {
        toast(`${data.length - prevCountRef.current} new listing(s) in queue`, "info");
      }
      prevCountRef.current = data.length;
    } catch {
      // Silently handle — queue may be empty
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 30_000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  // Keyboard shortcuts
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
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1
              className="text-3xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Review Queue
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">
              {listings.length} listing{listings.length !== 1 ? "s" : ""} awaiting review
              <span className="ml-3 text-xs text-slate-400">
                j/k navigate · a approve · s reject · space toggle
              </span>
            </p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-xl bg-white/50 animate-pulse" />
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
          </motion.div>
        ) : (
          <div className="space-y-3">
            {listings.map((listing) => {
              const addr = listing.address;
              const isExpanded = expandedId === listing.id;
              const data = expandedData[listing.id];

              return (
                <motion.div key={listing.id} layout>
                  <GlassCard tilt={false}>
                    {/* Row */}
                    <div
                      className="flex items-center gap-4 cursor-pointer"
                      onClick={() => toggleExpand(listing.id)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--color-text)] truncate">
                          {addr.street || "Untitled"}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)]">
                          {[addr.city, addr.state].filter(Boolean).join(", ")}
                          {" · "}
                          {new Date(listing.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Badge state={listing.state} />
                      <div className="flex gap-2">
                        <Button
                          variant="primary"
                          onClick={(e) => { e.stopPropagation(); handleApprove(listing.id); }}
                          loading={actionLoading === listing.id}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          onClick={(e) => { e.stopPropagation(); setRejectingId(listing.id); }}
                        >
                          Reject
                        </Button>
                      </div>
                      <svg
                        className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>

                    {/* Expanded detail panel */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-4 mt-4 border-t border-white/20">
                            {!data ? (
                              <div className="h-24 flex items-center justify-center">
                                <div className="w-5 h-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
                              </div>
                            ) : data.selections.length === 0 ? (
                              <p className="text-sm text-[var(--color-text-secondary)] text-center py-4">
                                No packaged photos yet.
                              </p>
                            ) : (
                              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                                {data.selections.map((sel) => (
                                  <div
                                    key={`${sel.asset_id}-${sel.position}`}
                                    className="relative aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 rounded-lg overflow-hidden group"
                                  >
                                    <div className="absolute inset-0 flex items-center justify-center">
                                      <span className="text-[10px] font-mono text-slate-400 px-1 truncate">
                                        #{sel.position + 1}
                                      </span>
                                    </div>
                                    <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5 flex items-center justify-between">
                                      <span className="text-[10px] text-white font-medium">
                                        {Math.round(sel.composite_score)}%
                                      </span>
                                      {sel.position === 0 && (
                                        <span className="text-[9px] text-orange-300 font-bold">HERO</span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Reject modal */}
                    <AnimatePresence>
                      {rejectingId === listing.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-4 mt-4 border-t border-red-200/40 space-y-3">
                            <p className="text-sm font-medium text-red-600">Rejection Reason</p>
                            <div className="flex flex-wrap gap-2">
                              {REASON_CODES.map((rc) => (
                                <button
                                  key={rc.value}
                                  onClick={() => setRejectReason(rc.value)}
                                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors cursor-pointer ${
                                    rejectReason === rc.value
                                      ? "bg-red-50 border-red-300 text-red-700"
                                      : "bg-white/50 border-white/30 text-[var(--color-text-secondary)] hover:bg-white/80"
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
                                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-red-400"
                              />
                            )}
                            <div className="flex gap-2">
                              <Button
                                variant="danger"
                                onClick={() => handleReject(listing.id)}
                                loading={actionLoading === listing.id}
                              >
                                Confirm Reject
                              </Button>
                              <Button
                                variant="secondary"
                                onClick={() => { setRejectingId(null); setRejectDetail(""); }}
                              >
                                Cancel
                              </Button>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}

export default function ReviewPage() {
  return (
    <ProtectedRoute>
      <ReviewQueue />
    </ProtectedRoute>
  );
}
