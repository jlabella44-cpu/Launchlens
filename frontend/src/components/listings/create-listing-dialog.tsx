"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AddressAutocomplete } from "@/components/ui/address-autocomplete";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import type { ListingResponse } from "@/lib/types";

const ADDON_OPTIONS = [
  { type: "ai_video_tour", label: "AI Video Tour", cost: 1 },
  { type: "3d_floorplan", label: "3D Floorplan", cost: 1 },
  { type: "social_pack", label: "Social Media Pack", cost: 1 },
] as const;

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
  const { billingModel, creditBalance, listingCreditCost, canAffordListing, refresh } = usePlan();

  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [zip, setZip] = useState("");
  const [beds, setBeds] = useState("");
  const [baths, setBaths] = useState("");
  const [sqft, setSqft] = useState("");
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedAddons, setSelectedAddons] = useState<Set<string>>(new Set());

  const addonCost = selectedAddons.size; // 1 credit each
  const totalCost = listingCreditCost + addonCost;
  const canAfford = creditBalance !== null ? creditBalance >= totalCost : true;
  const isCredit = billingModel === "credit";

  function toggleAddon(type: string) {
    setSelectedAddons((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const listing = await apiClient.createListing({
        address: { street, city, state, zip },
        metadata: {
          beds: Number(beds),
          baths: Number(baths),
          sqft: Number(sqft),
          price: Number(price),
        },
      });

      // Activate selected add-ons
      if (isCredit && selectedAddons.size > 0) {
        await Promise.all(
          Array.from(selectedAddons).map((type) =>
            apiClient.activateAddon(listing.id, type).catch(() => {})
          )
        );
      }

      await refresh();
      onCreated(listing);
      onClose();
      setStreet("");
      setCity("");
      setState("");
      setZip("");
      setBeds("");
      setBaths("");
      setSqft("");
      setPrice("");
      setSelectedAddons(new Set());
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
            <div className="glass w-full max-w-lg rounded-2xl p-8 shadow-xl max-h-[90vh] overflow-y-auto">
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
                  <AddressAutocomplete
                    value={street}
                    onChange={(val) => setStreet(val)}
                    onAddressSelect={(addr) => {
                      setStreet(addr.street);
                      setCity(addr.city);
                      setState(addr.state);
                      setZip(addr.zip);
                    }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
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
                  <div>
                    <label htmlFor="zip" className="block text-sm font-medium mb-1">
                      ZIP
                    </label>
                    <input
                      id="zip"
                      value={zip}
                      onChange={(e) => setZip(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                      placeholder="78701"
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
                      min="1"
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
                      min="1"
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
                      min="1"
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

                {/* Credit cost preview + Add-ons */}
                {isCredit && (
                  <div className="border border-[var(--color-border)] rounded-lg p-4 space-y-3">
                    <p className="text-sm font-medium">
                      This listing will use{" "}
                      <span className="text-[var(--color-primary)] font-bold">{listingCreditCost}</span>{" "}
                      credit{listingCreditCost !== 1 ? "s" : ""}.
                      Balance:{" "}
                      <span className="font-bold">{creditBalance ?? 0} credits</span>
                    </p>

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">
                        Add-ons (+1 credit each)
                      </p>
                      {ADDON_OPTIONS.map((addon) => (
                        <label
                          key={addon.type}
                          className="flex items-center gap-3 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedAddons.has(addon.type)}
                            onChange={() => toggleAddon(addon.type)}
                            className="w-4 h-4 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                          />
                          <span className="text-sm">{addon.label}</span>
                          <span className="text-xs text-[var(--color-text-secondary)] ml-auto">
                            +{addon.cost} credit
                          </span>
                        </label>
                      ))}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)]">
                      <span className="text-sm font-semibold">Total</span>
                      <span className="text-sm font-bold text-[var(--color-primary)]">
                        {totalCost} credit{totalCost !== 1 ? "s" : ""}
                      </span>
                    </div>

                    {!canAfford && (
                      <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                        Insufficient credits.{" "}
                        <Link
                          href="/billing"
                          className="underline font-medium"
                          onClick={onClose}
                        >
                          Buy Credits
                        </Link>
                      </p>
                    )}
                  </div>
                )}

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
                  <Button
                    type="submit"
                    loading={loading}
                    disabled={isCredit && !canAfford}
                    className="flex-1"
                  >
                    {isCredit ? `Create (${totalCost} credit${totalCost !== 1 ? "s" : ""})` : "Create Listing"}
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
