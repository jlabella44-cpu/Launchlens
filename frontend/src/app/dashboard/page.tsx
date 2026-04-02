"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ListingCard } from "@/components/listings/listing-card";
import { CreateListingDialog } from "@/components/listings/create-listing-dialog";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";
import type {
  CreditBalance,
  ListingResponse,
  UsageResponse,
  BrandKitResponse,
  PipelineStatusResponse,
} from "@/lib/types";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <GlassCard tilt={false} className="text-center">
      <p className="text-2xl sm:text-3xl font-bold text-[var(--color-primary)]">
        {value}
      </p>
      <p className="text-xs sm:text-sm text-[var(--color-text-secondary)] mt-1">
        {label}
      </p>
    </GlassCard>
  );
}

function DashboardContent() {
  const { user } = useAuth();
  const [credits, setCredits] = useState<CreditBalance | null>(null);
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [brandKit, setBrandKit] = useState<BrandKitResponse | null>(null);
  const [pipelineData, setPipelineData] = useState<
    Map<string, PipelineStatusResponse>
  >(new Map());
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  useEffect(() => {
    async function fetchAll() {
      const [creditsRes, listingsRes, usageRes, brandRes] =
        await Promise.allSettled([
          apiClient.getCreditBalance(),
          apiClient.getListings(),
          apiClient.getUsage(),
          apiClient.getBrandKit(),
        ]);

      if (creditsRes.status === "fulfilled") setCredits(creditsRes.value);
      if (listingsRes.status === "fulfilled") setListings(listingsRes.value);
      if (usageRes.status === "fulfilled") setUsage(usageRes.value);
      if (brandRes.status === "fulfilled") setBrandKit(brandRes.value);

      // Fetch pipeline status for active listings
      if (listingsRes.status === "fulfilled") {
        const activeStates = [
          "uploading",
          "analyzing",
          "exporting",
          "in_review",
        ];
        const active = listingsRes.value
          .filter((l: ListingResponse) => activeStates.includes(l.state))
          .slice(0, 5);

        if (active.length > 0) {
          const pipeResults = await Promise.allSettled(
            active.map((l: ListingResponse) =>
              apiClient.getPipelineStatus(l.id)
            )
          );
          const map = new Map<string, PipelineStatusResponse>();
          pipeResults.forEach((r, i) => {
            if (r.status === "fulfilled") {
              map.set(active[i].id, r.value);
            }
          });
          setPipelineData(map);
        }
      }

      setLoading(false);
    }

    fetchAll();
  }, []);

  const recentListings = listings.slice(0, 5);
  const reviewCount = listings.filter(
    (l) => l.state === "awaiting_review"
  ).length;
  const activeStates = ["uploading", "analyzing", "exporting", "in_review"];
  const activeListings = listings.filter((l) =>
    activeStates.includes(l.state)
  );
  const brandConfigured = !!(
    brandKit &&
    (brandKit.logo_url || brandKit.brokerage_name || brandKit.primary_color)
  );

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  if (loading) {
    return (
      <>
        <Nav />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
          <div className="h-10 w-64 rounded-lg bg-white/50 animate-pulse" />
          <div className="h-32 rounded-xl bg-white/50 animate-pulse" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-24 rounded-xl bg-white/50 animate-pulse"
              />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 h-64 rounded-xl bg-white/50 animate-pulse" />
            <div className="h-64 rounded-xl bg-white/50 animate-pulse" />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Nav />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6"
      >
        {/* Header */}
        <div>
          <h1
            className="text-2xl sm:text-3xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            {greeting()}, {user?.name?.split(" ")[0] || "there"}
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            {new Date().toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </p>
        </div>

        {/* Credit Hero */}
        <GlassCard tilt={false}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Credit Balance
              </p>
              <p className="text-4xl sm:text-5xl font-bold text-[var(--color-primary)]">
                {credits?.balance ?? 0}
              </p>
              <div className="flex items-center gap-3 mt-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                  {credits?.tier || "Free"} tier
                </span>
                {credits?.per_listing_credit_cost && (
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    {credits.per_listing_credit_cost} credit/listing
                  </span>
                )}
              </div>
              {credits?.period_end && (
                <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                  Renews{" "}
                  {new Date(credits.period_end).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </p>
              )}
            </div>
            <Link href="/billing">
              <Button variant="primary">Buy Credits</Button>
            </Link>
          </div>
        </GlassCard>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <StatCard
              label="Total Listings"
              value={usage?.total_listings ?? listings.length}
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18 }}
          >
            <StatCard
              label="This Month"
              value={usage?.listings_this_month ?? 0}
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.26 }}
          >
            <StatCard label="Awaiting Review" value={reviewCount} />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.34 }}
          >
            <StatCard label="Total Assets" value={usage?.total_assets ?? 0} />
          </motion.div>
        </div>

        {/* Two-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Recent Listings */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2
                className="text-lg font-semibold text-[var(--color-text)]"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Recent Listings
              </h2>
              <Link
                href="/listings"
                className="text-sm text-[var(--color-primary)] hover:underline"
              >
                View all →
              </Link>
            </div>
            {recentListings.length === 0 ? (
              <GlassCard tilt={false} className="text-center py-12">
                <p className="text-[var(--color-text-secondary)]">
                  No listings yet. Create your first one!
                </p>
                <Button
                  variant="primary"
                  className="mt-4"
                  onClick={() => setShowCreateDialog(true)}
                >
                  Create First Listing
                </Button>
              </GlassCard>
            ) : (
              <div className="space-y-3">
                {recentListings.map((listing, i) => (
                  <motion.div
                    key={listing.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.08 * i }}
                  >
                    <ListingCard
                      listing={listing}
                      onDeleted={(id) => setListings((prev) => prev.filter((l) => l.id !== id))}
                    />
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Sidebar */}
          <div className="space-y-4">
            {/* Quick Actions */}
            <GlassCard tilt={false}>
              <h3
                className="text-base font-semibold text-[var(--color-text)] mb-3"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Quick Actions
              </h3>
              <div className="space-y-2">
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={() => setShowCreateDialog(true)}
                >
                  + New Listing
                </Button>
                <Link href="/review" className="block">
                  <Button variant="secondary" className="w-full">
                    Review Queue
                    {reviewCount > 0 && (
                      <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs font-bold rounded-full bg-[var(--color-cta)] text-white">
                        {reviewCount}
                      </span>
                    )}
                  </Button>
                </Link>
                <Link href="/settings" className="block">
                  <Button variant="secondary" className="w-full">
                    Settings
                  </Button>
                </Link>
              </div>
            </GlassCard>

            {/* Brand Kit Status */}
            <GlassCard tilt={false}>
              <h3
                className="text-base font-semibold text-[var(--color-text)] mb-3"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Brand Kit
              </h3>
              {brandConfigured ? (
                <div className="flex items-center gap-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-100">
                    <svg
                      className="w-4 h-4 text-green-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </span>
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text)]">
                      {brandKit?.brokerage_name || "Configured"}
                    </p>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Branding active on exports
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-[var(--color-text-secondary)] mb-2">
                    Set up your branding for flyers, watermarks, and exports.
                  </p>
                  <Link href="/settings">
                    <Button variant="secondary" className="w-full">
                      Set Up Brand Kit
                    </Button>
                  </Link>
                </div>
              )}
            </GlassCard>

            {/* Pipeline Activity */}
            {activeListings.length > 0 && (
              <GlassCard tilt={false}>
                <h3
                  className="text-base font-semibold text-[var(--color-text)] mb-3"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Pipeline Activity
                </h3>
                <div className="space-y-3">
                  {activeListings.slice(0, 3).map((listing) => {
                    const pipeline = pipelineData.get(listing.id);
                    return (
                      <Link
                        key={listing.id}
                        href={`/listings/${listing.id}`}
                        className="block"
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-[var(--color-text)] truncate max-w-[160px]">
                            {listing.address?.street || "Listing"}
                          </p>
                          <Badge state={listing.state} />
                        </div>
                        {pipeline && (
                          <div className="flex gap-1 mt-1.5">
                            {pipeline.steps.map((step) => (
                              <div
                                key={step.name}
                                className={`h-1.5 flex-1 rounded-full ${
                                  step.status === "completed"
                                    ? "bg-[var(--color-primary)]"
                                    : step.status === "in_progress"
                                    ? "bg-[var(--color-cta)]"
                                    : "bg-white/30"
                                }`}
                              />
                            ))}
                          </div>
                        )}
                      </Link>
                    );
                  })}
                  {activeListings.length > 3 && (
                    <p className="text-xs text-[var(--color-text-secondary)] text-center">
                      and {activeListings.length - 3} more processing...
                    </p>
                  )}
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      </motion.div>

      <CreateListingDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreated={(newListing) => {
          setListings((prev) => [newListing, ...prev]);
          setShowCreateDialog(false);
        }}
      />
    </>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
