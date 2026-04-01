"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { ListingCard } from "@/components/listings/listing-card";
import { CreateListingDialog } from "@/components/listings/create-listing-dialog";
import apiClient from "@/lib/api-client";
import type { ListingResponse } from "@/lib/types";

function ListingsDashboard() {
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showBrandBanner, setShowBrandBanner] = useState(false);

  useEffect(() => { document.title = "Listings | ListingJet"; }, []);

  useEffect(() => {
    Promise.all([
      apiClient.getListings(),
      apiClient.getBrandKit().catch(() => null),
    ])
      .then(([listings, kit]) => {
        setListings(listings);
        if (!kit) setShowBrandBanner(true);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load listings");
      })
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(listing: ListingResponse) {
    setListings((prev) => [listing, ...prev]);
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Brand Kit Banner */}
        {showBrandBanner && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 flex items-center justify-between rounded-xl bg-amber-50 border border-amber-200/60 overflow-hidden"
          >
            <div className="flex items-center gap-3 px-4 py-3">
              <div className="w-1 h-8 rounded-full bg-amber-400" />
              <p className="text-sm text-slate-600">
                Set up your brand kit for branded exports
              </p>
            </div>
            <Link
              href="/settings"
              className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[#F97316] hover:text-[#ea580c] transition-colors"
            >
              Configure Now
            </Link>
          </motion.div>
        )}

        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-4xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Your Listings
          </h1>
          <div className="flex items-end justify-between mt-2">
            <p className="text-sm text-slate-400">
              Manage and monitor your stratospheric property deployments in real-time.
            </p>
            <button
              onClick={() => setDialogOpen(true)}
              className="flex-shrink-0 px-5 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors inline-flex items-center gap-2 shadow-md shadow-orange-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Listing
            </button>
          </div>
        </div>

        {/* Content */}
        {error ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2 rounded-full border border-slate-200 text-sm font-medium text-slate-600 hover:border-slate-300 transition-colors"
            >
              Retry
            </button>
          </motion.div>
        ) : loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-2xl overflow-hidden">
                <div className="aspect-[4/3] bg-slate-100 animate-pulse" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
                  <div className="h-3 bg-slate-100 rounded animate-pulse w-1/2" />
                  <div className="h-6 bg-slate-100 rounded animate-pulse w-1/3 mt-4" />
                </div>
              </div>
            ))}
          </div>
        ) : listings.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              </svg>
            </div>
            <p className="text-lg text-slate-400 mb-4">
              No listings yet. Create your first one to get started.
            </p>
            <button
              onClick={() => setDialogOpen(true)}
              className="px-6 py-3 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors shadow-md shadow-orange-200"
            >
              Create First Listing
            </button>
          </motion.div>
        ) : (
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            initial="hidden"
            animate="show"
            variants={{
              hidden: {},
              show: { transition: { staggerChildren: 0.08 } },
            }}
          >
            {listings.map((listing) => (
              <motion.div
                key={listing.id}
                variants={{
                  hidden: { opacity: 0, y: 20 },
                  show: { opacity: 1, y: 0 },
                }}
              >
                <ListingCard listing={listing} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </main>

      <CreateListingDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={handleCreated}
      />
    </>
  );
}

export default function ListingsPage() {
  return (
    <ProtectedRoute>
      <ListingsDashboard />
    </ProtectedRoute>
  );
}
