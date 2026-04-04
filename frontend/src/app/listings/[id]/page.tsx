"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Badge } from "@/components/ui/badge";
import { PackageViewer } from "@/components/listings/package-viewer";
import { PipelineStatus } from "@/components/listings/pipeline-status";
import { AssetUploadForm } from "@/components/listings/asset-upload-form";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import type { ListingResponse, AssetResponse, PackageSelection } from "@/lib/types";
import { VideoPlayer } from "@/components/listings/video-player";
import { VideoUpload } from "@/components/listings/video-upload";
import { SocialPreview } from "@/components/listings/social-preview";
import { SharePanel } from "@/components/listings/share-panel";
import { ActivityLog } from "@/components/listings/activity-log";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";

function ListingDetail() {
  const params = useParams();
  const id = params.id as string;
  const { toast } = useToast();

  const [listing, setListing] = useState<ListingResponse | null>(null);
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [selections, setSelections] = useState<PackageSelection[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [shareOpen, setShareOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionDone, setActionDone] = useState("");
  const [showVideoUpload, setShowVideoUpload] = useState(false);
  const [assetView, setAssetView] = useState<"grid" | "list">("grid");

  const fetchData = useCallback(async () => {
    try {
      const [l, a] = await Promise.all([
        apiClient.getListing(id),
        apiClient.getAssets(id),
      ]);
      setListing(l);
      setAssets(a);

      const packageStates = [
        "awaiting_review", "in_review", "approved", "exporting", "delivered",
      ];
      if (packageStates.includes(l.state)) {
        const pkg = await apiClient.getPackage(id);
        setSelections(pkg);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load listing";
      setFetchError(msg);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { document.title = "Listing Detail | ListingJet"; }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const PROCESSING_STATES = ["uploading", "analyzing", "exporting"];
    if (!listing || !PROCESSING_STATES.includes(listing.state)) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [listing?.state, fetchData]);

  async function handleStartReview() {
    setActionLoading(true);
    try {
      const res = await apiClient.startReview(id);
      setListing((prev) => (prev ? { ...prev, state: res.state } : prev));
      toast("Review started", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to start review", "error");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleApprove() {
    setActionLoading(true);
    try {
      const res = await apiClient.approveListing(id);
      setListing((prev) => (prev ? { ...prev, state: res.state } : prev));
      setActionDone("approved");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to approve", "error");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleExport(mode: "mls" | "marketing") {
    try {
      const res = await apiClient.getExport(id, mode);
      window.open(res.download_url, "_blank");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Export not available yet", "error");
    }
  }

  async function handleRetryPipeline() {
    setActionLoading(true);
    try {
      const res = await apiClient.retryPipeline(id);
      setListing((prev) => (prev ? { ...prev, state: res.state } : prev));
      toast("Pipeline restarted", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to retry", "error");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
        <div className="w-8 h-8 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
        <div className="text-center">
          <p className="text-slate-400 mb-4">
            {fetchError || "Listing not found."}
          </p>
          {fetchError && (
            <button
              onClick={() => { setFetchError(""); setLoading(true); fetchData(); }}
              className="px-5 py-2 rounded-full bg-[#F97316] text-white text-sm font-semibold"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  const addr = listing.address;
  const meta = listing.metadata;
  const showActions = ["awaiting_review", "in_review", "approved", "exporting", "delivered"].includes(listing.state);
  const showVideo = ["approved", "exporting", "delivered"].includes(listing.state);

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Dashboard", href: "/dashboard" },
            { label: "Listings", href: "/listings" },
            { label: listing?.address?.street || listing?.address?.city || "Listing" },
          ]}
        />

        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <h1
                className="text-3xl sm:text-4xl font-bold text-[var(--color-text)]"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                {addr.street || "Listing"}
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                {[addr.city, addr.state, addr.zip].filter(Boolean).join(", ")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShareOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text-secondary)] hover:border-[#F97316] hover:text-[#F97316] transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
                Share
              </button>
              <Badge state={listing.state} />
            </div>
          </div>
        </div>

        {/* Share Panel */}
        <SharePanel listingId={id} isOpen={shareOpen} onClose={() => setShareOpen(false)} />

        {/* Pipeline Status */}
        <div className="mb-8">
          <PipelineStatus state={listing.state} />
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Upload + Assets */}
          <div className="space-y-6">
            {/* Upload */}
            <AssetUploadForm listingId={id} onUploaded={fetchData} />

            {/* Assets Grid */}
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3
                  className="text-base font-semibold text-[var(--color-text)]"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Assets
                  <span className="ml-2 text-xs text-slate-400 font-normal">{assets.length} photos</span>
                </h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setAssetView("grid")}
                    className={`p-1.5 rounded ${assetView === "grid" ? "text-[#F97316]" : "text-slate-300"}`}
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                      <rect x="0" y="0" width="7" height="7" rx="1" />
                      <rect x="9" y="0" width="7" height="7" rx="1" />
                      <rect x="0" y="9" width="7" height="7" rx="1" />
                      <rect x="9" y="9" width="7" height="7" rx="1" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setAssetView("list")}
                    className={`p-1.5 rounded ${assetView === "list" ? "text-[#F97316]" : "text-slate-300"}`}
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                      <rect x="0" y="1" width="16" height="3" rx="1" />
                      <rect x="0" y="6.5" width="16" height="3" rx="1" />
                      <rect x="0" y="12" width="16" height="3" rx="1" />
                    </svg>
                  </button>
                </div>
              </div>

              {assets.length === 0 ? (
                <p className="text-sm text-slate-400 py-4 text-center">
                  No assets yet. Upload photos above.
                </p>
              ) : assetView === "grid" ? (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {assets.map((a) => (
                    <div
                      key={a.id}
                      className="aspect-square rounded-xl bg-gradient-to-br from-slate-100 to-slate-50 overflow-hidden flex items-center justify-center"
                    >
                      {a.thumbnail_url ? (
                        <img
                          src={a.thumbnail_url}
                          alt={a.file_path.split("/").pop() || "Photo"}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <svg className="w-6 h-6 text-slate-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-80 overflow-y-auto">
                  {assets.map((a) => (
                    <div
                      key={a.id}
                      className="aspect-square rounded-lg overflow-hidden bg-slate-100 border border-slate-200"
                    >
                      {a.thumbnail_url ? (
                        <img
                          src={a.thumbnail_url}
                          alt={a.file_path.split('/').pop() || 'Photo'}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <svg className="w-6 h-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Actions + Package + Video + Social */}
          <div className="space-y-6">
            {/* Action Buttons */}
            {showActions && (
              <div className="flex flex-wrap gap-3">
                {listing.state === "awaiting_review" && (
                  <button
                    onClick={handleStartReview}
                    disabled={actionLoading}
                    className="px-5 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors disabled:opacity-50 shadow-md shadow-orange-200 inline-flex items-center gap-2"
                  >
                    {actionLoading ? (
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      </svg>
                    )}
                    Start Review
                  </button>
                )}
                {listing.state === "in_review" && (
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="px-5 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors disabled:opacity-50 shadow-md shadow-orange-200"
                  >
                    Approve Package
                  </button>
                )}
                {["approved", "exporting", "delivered"].includes(listing.state) && (
                  <>
                    <Link href={`/listings/${id}/export`}>
                      <button className="px-5 py-2.5 rounded-full border border-slate-200 text-sm font-semibold text-slate-600 hover:border-slate-300 transition-colors">
                        Export Packages
                      </button>
                    </Link>
                    <button
                      onClick={() => handleExport("marketing")}
                      className="px-5 py-2.5 rounded-full bg-[#0B1120] hover:bg-[#1a2744] text-white text-sm font-semibold transition-colors inline-flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Quick Download
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Error / Retry State */}
            {["failed", "pipeline_timeout", "uploading", "analyzing"].includes(listing.state) && (
              <div className={`rounded-2xl p-5 ${
                ["uploading", "analyzing"].includes(listing.state)
                  ? "bg-amber-50 border border-amber-200"
                  : "bg-red-50 border border-red-200"
              }`}>
                <h4 className={`font-semibold mb-1 ${
                  ["uploading", "analyzing"].includes(listing.state) ? "text-amber-800" : "text-red-800"
                }`}>
                  {["uploading", "analyzing"].includes(listing.state)
                    ? "Processing Stalled"
                    : "Course Correction Required"}
                </h4>
                <p className={`text-sm mb-4 ${
                  ["uploading", "analyzing"].includes(listing.state) ? "text-amber-600" : "text-red-600"
                }`}>
                  {listing.state === "pipeline_timeout"
                    ? "Flight delayed. Processing timed out — this can happen with large photo sets."
                    : ["uploading", "analyzing"].includes(listing.state)
                    ? "This listing appears stuck. Click retry to restart the pipeline."
                    : "Turbulence detected. Something went wrong during processing."}
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={handleRetryPipeline}
                    disabled={actionLoading}
                    className="px-5 py-2 rounded-full bg-[#F97316] text-white text-sm font-semibold disabled:opacity-50"
                  >
                    Retry Processing
                  </button>
                  <Link href="/listings">
                    <button className="px-5 py-2 rounded-full border border-slate-200 text-sm text-slate-600">
                      Back to Listings
                    </button>
                  </Link>
                </div>
              </div>
            )}

            {actionDone === "approved" && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 text-green-600 bg-green-50 rounded-xl px-4 py-3"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm font-medium">
                  Autopilot engaged. Your marketing assets are being deployed.
                </span>
              </motion.div>
            )}

            {/* Curated Package */}
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <h3
                className="text-base font-semibold text-[var(--color-text)] mb-3"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Curated Package
                {selections.length > 0 && (
                  <span className="ml-2 text-xs text-slate-400 font-normal">{selections.length} photos</span>
                )}
              </h3>
              <PackageViewer selections={selections} />
            </div>

            {/* Video Assets */}
            {showVideo && (
              <div className="bg-white rounded-2xl border border-slate-100 p-5">
                <h3
                  className="text-base font-semibold text-[var(--color-text)] mb-3"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Video Assets
                </h3>
                <VideoPlayer
                  listingId={id}
                  onNoVideo={() => setShowVideoUpload(true)}
                />
                {showVideoUpload && (
                  <div className="mt-4">
                    <VideoUpload
                      listingId={id}
                      onUploaded={() => {
                        setShowVideoUpload(false);
                        fetchData();
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Social Cuts */}
            {showVideo && (
              <div className="bg-white rounded-2xl border border-slate-100 p-5">
                <h3
                  className="text-base font-semibold text-[var(--color-text)] mb-3"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Social Cuts
                </h3>
                <SocialPreview listingId={id} />
              </div>
            )}
          </div>
        </div>

        {/* Activity Log */}
        <div className="mt-10">
          <ActivityLog listingId={id} />
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-slate-100 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-300">
          <span>ListingJet</span>
          <div className="flex items-center gap-6">
            <span className="hover:text-slate-400 cursor-pointer">Safety Manual</span>
            <span className="hover:text-slate-400 cursor-pointer">Flight Logs</span>
            <span className="hover:text-slate-400 cursor-pointer">Tower Support</span>
          </div>
          <span>© {new Date().getFullYear()} ListingJet Command. All rights reserved.</span>
        </footer>
      </main>
    </>
  );
}

export default function ListingDetailPage() {
  return (
    <ProtectedRoute>
      <ListingDetail />
    </ProtectedRoute>
  );
}
