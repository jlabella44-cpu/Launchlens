"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { ListingCard } from "@/components/listings/listing-card";
import { CreateListingDialog } from "@/components/listings/create-listing-dialog";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";
import type { ListingResponse } from "@/lib/types";
import { useToast } from "@/contexts/toast-context";

function ListingsDashboard() {
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const toast = useToast();

  function loadListings() {
    setFetchError(null);
    setLoading(true);
    apiClient
      .getListings()
      .then(setListings)
      .catch((err: any) => {
        setFetchError(err.message || "Failed to load listings");
        toast.error("Failed to load listings");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadListings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleCreated(listing: ListingResponse) {
    setListings((prev) => [listing, ...prev]);
    toast.success("Listing created");
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1
              className="text-3xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Listings
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Manage your property listings
            </p>
          </div>
          <Button onClick={() => setDialogOpen(true)}>New Listing</Button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-48 rounded-xl bg-white/50 animate-pulse"
              />
            ))}
          </div>
        ) : fetchError ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3l9.66 16.5H2.34L12 3z" />
              </svg>
            </div>
            <p className="text-[var(--color-text-secondary)] mb-4">{fetchError}</p>
            <Button onClick={loadListings}>Retry</Button>
          </div>
        ) : listings.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <p className="text-lg text-[var(--color-text-secondary)] mb-4">
              No listings yet. Create your first one to get started.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Create First Listing
            </Button>
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
