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

function ListingsDashboard() {
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    apiClient
      .getListings()
      .then(setListings)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(listing: ListingResponse) {
    setListings((prev) => [listing, ...prev]);
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
