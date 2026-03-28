"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { PackageViewer } from "@/components/listings/package-viewer";
import { PipelineStatus } from "@/components/listings/pipeline-status";
import { AssetUploadForm } from "@/components/listings/asset-upload-form";
import apiClient from "@/lib/api-client";
import type { ListingResponse, AssetResponse, PackageSelection } from "@/lib/types";
import { VideoPlayer } from "@/components/listings/video-player";
import { VideoUpload } from "@/components/listings/video-upload";
import { SocialPreview } from "@/components/listings/social-preview";

const SceneWrapper = dynamic(
  () => import("@/components/three/scene-wrapper").then((m) => ({ default: m.SceneWrapper })),
  { ssr: false }
);
const PhotoOrbit = dynamic(
  () => import("@/components/three/photo-orbit").then((m) => ({ default: m.PhotoOrbit })),
  { ssr: false }
);

function ListingDetail() {
  const params = useParams();
  const id = params.id as string;

  const [listing, setListing] = useState<ListingResponse | null>(null);
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [selections, setSelections] = useState<PackageSelection[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionDone, setActionDone] = useState("");
  const [showVideoUpload, setShowVideoUpload] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [l, a] = await Promise.all([
        apiClient.getListing(id),
        apiClient.getAssets(id),
      ]);
      setListing(l);
      setAssets(a);

      // Load package if past packaging stage
      const packageStates = [
        "awaiting_review", "in_review", "approved", "exporting", "delivered",
      ];
      if (packageStates.includes(l.state)) {
        const pkg = await apiClient.getPackage(id);
        setSelections(pkg);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleStartReview() {
    setActionLoading(true);
    try {
      const res = await apiClient.startReview(id);
      setListing((prev) => (prev ? { ...prev, state: res.state } : prev));
    } catch (err) {
      console.error(err);
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
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleExport(mode: "mls" | "marketing") {
    try {
      const res = await apiClient.getExport(id, mode);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert(err.message || "Export not available yet");
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[var(--color-text-secondary)]">Listing not found.</p>
      </div>
    );
  }

  const addr = listing.address;
  const meta = listing.metadata;

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/listings"
            className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block cursor-pointer min-h-[44px] flex items-center touch-manipulation"
          >
            &larr; Back to Listings
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1
              className="text-2xl sm:text-3xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              {addr.street || "Listing"}
            </h1>
            <Badge state={listing.state} />
          </div>
          {(addr.city || addr.state) && (
            <p className="text-[var(--color-text-secondary)] mt-1">
              {[addr.city, addr.state].filter(Boolean).join(", ")}
              {meta.beds != null && ` | ${meta.beds} beds`}
              {meta.baths != null && ` | ${meta.baths} baths`}
              {meta.sqft != null && ` | ${meta.sqft.toLocaleString()} sqft`}
            </p>
          )}
        </div>

        {/* Pipeline Status */}
        <div className="mb-8">
          <PipelineStatus state={listing.state} />
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Assets + Upload */}
          <div className="space-y-6">
            <AssetUploadForm listingId={id} onUploaded={fetchData} />

            <GlassCard tilt={false}>
              <h3
                className="text-lg font-semibold mb-3"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Assets ({assets.length})
              </h3>
              {assets.length === 0 ? (
                <p className="text-sm text-[var(--color-text-secondary)]">
                  No assets yet. Register S3 paths above.
                </p>
              ) : (
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {assets.map((a) => (
                    <div
                      key={a.id}
                      className="text-xs font-mono text-[var(--color-text-secondary)] px-2 py-1 rounded bg-white/50 truncate"
                    >
                      {a.file_path}
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          </div>

          {/* Right: Package + Actions */}
          <div className="space-y-6">
            {/* 3D Photo Orbit — hidden on mobile for performance */}
            {selections.length > 0 && (
              <div className="hidden lg:block">
                <SceneWrapper
                  className="w-full h-[300px]"
                  camera={{ position: [0, 2, 5], fov: 50 }}
                >
                  <PhotoOrbit photos={selections} heroIndex={0} />
                </SceneWrapper>
              </div>
            )}

            <PackageViewer selections={selections} />

            {/* Action buttons */}
            <GlassCard tilt={false}>
              <h3
                className="text-lg font-semibold mb-4"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Actions
              </h3>
              <div className="flex flex-col sm:flex-row flex-wrap gap-3">
                {listing.state === "awaiting_review" && (
                  <Button onClick={handleStartReview} loading={actionLoading}>
                    Start Review
                  </Button>
                )}
                {listing.state === "in_review" && (
                  <Button onClick={handleApprove} loading={actionLoading}>
                    Approve Package
                  </Button>
                )}
                {["approved", "exporting", "delivered"].includes(listing.state) && (
                  <>
                    <Link href={`/listings/${id}/export`}>
                      <Button variant="secondary">Export Packages</Button>
                    </Link>
                    <Button onClick={() => handleExport("marketing")}>
                      Quick Download Marketing
                    </Button>
                  </>
                )}
              </div>

              {actionDone === "approved" && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-4 flex items-center gap-2 text-green-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium">
                    Package approved! Pipeline is generating your export bundles.
                  </span>
                </motion.div>
              )}
            </GlassCard>
          </div>
        </div>

        {/* Video + Social Section */}
        {["approved", "exporting", "delivered"].includes(listing.state) && (
          <div className="mt-8 space-y-6">
            <VideoPlayer
              listingId={id}
              onNoVideo={() => setShowVideoUpload(true)}
            />
            {showVideoUpload && (
              <VideoUpload
                listingId={id}
                onUploaded={() => {
                  setShowVideoUpload(false);
                  fetchData();
                }}
              />
            )}
            <SocialPreview listingId={id} />
          </div>
        )}
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
