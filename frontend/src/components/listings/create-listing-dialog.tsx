"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";
import type { ListingResponse } from "@/lib/types";

interface CreateListingDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (listing: ListingResponse) => void;
}

export function CreateListingDialog({
  open,
  onClose,
  onCreated,
}: CreateListingDialogProps) {
  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [beds, setBeds] = useState("");
  const [baths, setBaths] = useState("");
  const [sqft, setSqft] = useState("");
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const listing = await apiClient.createListing({
        address: { street, city, state },
        metadata: {
          beds: Number(beds),
          baths: Number(baths),
          sqft: Number(sqft),
          price: Number(price),
        },
      });
      onCreated(listing);
      onClose();
      setStreet("");
      setCity("");
      setState("");
      setBeds("");
      setBaths("");
      setSqft("");
      setPrice("");
    } catch (err: any) {
      setError(err.message || "Failed to create listing");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="glass w-full max-w-lg rounded-2xl p-8 shadow-xl">
              <h2
                className="text-xl font-bold mb-6"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                New Listing
              </h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="street" className="block text-sm font-medium mb-1">
                    Street Address
                  </label>
                  <input
                    id="street"
                    required
                    value={street}
                    onChange={(e) => setStreet(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    placeholder="123 Main Street"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="city" className="block text-sm font-medium mb-1">
                      City
                    </label>
                    <input
                      id="city"
                      required
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    />
                  </div>
                  <div>
                    <label htmlFor="state" className="block text-sm font-medium mb-1">
                      State
                    </label>
                    <input
                      id="state"
                      required
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                      placeholder="TX"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <label htmlFor="beds" className="block text-sm font-medium mb-1">
                      Beds
                    </label>
                    <input
                      id="beds"
                      type="number"
                      min="0"
                      required
                      value={beds}
                      onChange={(e) => setBeds(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    />
                  </div>
                  <div>
                    <label htmlFor="baths" className="block text-sm font-medium mb-1">
                      Baths
                    </label>
                    <input
                      id="baths"
                      type="number"
                      min="0"
                      required
                      value={baths}
                      onChange={(e) => setBaths(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    />
                  </div>
                  <div>
                    <label htmlFor="sqft" className="block text-sm font-medium mb-1">
                      Sqft
                    </label>
                    <input
                      id="sqft"
                      type="number"
                      min="0"
                      required
                      value={sqft}
                      onChange={(e) => setSqft(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    />
                  </div>
                  <div>
                    <label htmlFor="price" className="block text-sm font-medium mb-1">
                      Price
                    </label>
                    <input
                      id="price"
                      type="number"
                      min="0"
                      required
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    />
                  </div>
                </div>

                {error && (
                  <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                    {error}
                  </p>
                )}

                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={onClose}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button type="submit" loading={loading} className="flex-1">
                    Create Listing
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
