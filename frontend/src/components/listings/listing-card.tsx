"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import apiClient from "@/lib/api-client";
import type { ListingResponse } from "@/lib/types";

interface ListingCardProps {
  listing: ListingResponse;
  onDeleted?: (listingId: string) => void;
}

export function ListingCard({ listing, onDeleted }: ListingCardProps) {
  const router = useRouter();
  const { address, metadata, state } = listing;
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const price = metadata.price
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(metadata.price)
    : null;

  const isDelivered = state === "delivered" || state === "approved";
  const canDelete = true;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/listings/${listing.id}`)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(`/listings/${listing.id}`); } }}
      aria-label={`View listing at ${address.street || "New Listing"}`}
      className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group border border-slate-100"
    >
      {/* Photo Thumbnail */}
      <div className="relative aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 overflow-hidden">
        {listing.thumbnail_url ? (
          <Image
            src={listing.thumbnail_url}
            alt={address.street || "Property photo"}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-10 h-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 22V12h6v10" />
            </svg>
          </div>
        )}
        <div className="absolute top-3 left-3">
          <Badge state={state} />
        </div>
      </div>

      <div className="p-4">
        <h3
          className="text-base font-semibold text-[var(--color-text)] group-hover:text-[#F97316] transition-colors truncate"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          {address.street || "New Listing"}
        </h3>
        {(address.city || address.state) && (
          <p className="text-xs text-slate-400 mt-0.5 uppercase tracking-wide">
            {[address.city, address.state].filter(Boolean).join(", ")}
          </p>
        )}

        {(metadata.beds != null || metadata.baths != null || metadata.sqft != null) && (
          <div className="flex items-center gap-0 mt-3 text-xs text-slate-500">
            {metadata.beds != null && (
              <div className="text-center">
                <span className="font-semibold text-[var(--color-text)]">{metadata.beds}</span>
                <span className="ml-1 text-[10px] uppercase tracking-wider text-slate-400">Beds</span>
              </div>
            )}
            {metadata.baths != null && (
              <>
                <span className="mx-2 text-slate-200">|</span>
                <div className="text-center">
                  <span className="font-semibold text-[var(--color-text)]">{metadata.baths}</span>
                  <span className="ml-1 text-[10px] uppercase tracking-wider text-slate-400">Baths</span>
                </div>
              </>
            )}
            {metadata.sqft != null && (
              <>
                <span className="mx-2 text-slate-200">|</span>
                <div className="text-center">
                  <span className="font-semibold text-[var(--color-text)]">{metadata.sqft.toLocaleString()}</span>
                  <span className="ml-1 text-[10px] uppercase tracking-wider text-slate-400">Sqft</span>
                </div>
              </>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mt-4">
          {price ? (
            <p className="text-lg font-bold text-[var(--color-text)]">{price}</p>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            {canDelete && (
              <button
                onClick={(e) => { e.stopPropagation(); setConfirming(true); }}
                className="w-8 h-8 rounded-full border border-slate-200 flex items-center justify-center text-slate-400 hover:border-red-300 hover:text-red-500 transition-colors"
                title="Delete listing"
                aria-label="Delete listing"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
            {isDelivered ? (
              <button className="px-3 py-1 rounded-full bg-[#F97316] text-white text-[11px] font-semibold uppercase tracking-wide hover:bg-[#ea580c] transition-colors">
                View MLS
              </button>
            ) : (
              <div className="w-8 h-8 rounded-full border border-slate-200 flex items-center justify-center group-hover:border-[#F97316] group-hover:text-[#F97316] text-slate-400 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {confirming && (
          <motion.div
            key="delete-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`delete-listing-title-${listing.id}`}
            onClick={(e) => {
              e.stopPropagation();
              if (!deleting) setConfirming(false);
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-2xl border border-slate-100 bg-white p-6 shadow-2xl"
            >
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <h3
                    id={`delete-listing-title-${listing.id}`}
                    className="text-base font-bold text-[var(--color-text)]"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    Delete this listing?
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                    <span className="font-semibold text-[var(--color-text)]">
                      {address.street || "Untitled listing"}
                    </span>
                    {address.city ? ` · ${address.city}` : ""} will be
                    permanently deleted along with its photos, packages, and
                    video assets. This cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-5">
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setConfirming(false); }}
                  disabled={deleting}
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-slate-500 border border-slate-200 hover:text-slate-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={async (e) => {
                    e.stopPropagation();
                    setDeleting(true);
                    try {
                      await apiClient.deleteListing(listing.id);
                      onDeleted?.(listing.id);
                    } catch {
                      setDeleting(false);
                      setConfirming(false);
                    }
                  }}
                  disabled={deleting}
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-50"
                >
                  {deleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
