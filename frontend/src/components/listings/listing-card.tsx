"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
  const canDelete = !isDelivered && state !== "processing";

  return (
    <div
      onClick={() => router.push(`/listings/${listing.id}`)}
      className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group border border-slate-100"
    >
      {/* Photo Thumbnail */}
      <div className="relative aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 overflow-hidden">
        {listing.thumbnail_url ? (
          <img
            src={listing.thumbnail_url}
            alt={address.street || "Property photo"}
            className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
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
              confirming ? (
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <button
                    disabled={deleting}
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
                    className="px-2 py-1 rounded-full bg-red-500 text-white text-[11px] font-semibold uppercase tracking-wide hover:bg-red-600 transition-colors disabled:opacity-50"
                  >
                    {deleting ? "..." : "Confirm"}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirming(false); }}
                    className="px-2 py-1 rounded-full border border-slate-200 text-slate-400 text-[11px] font-semibold uppercase tracking-wide hover:border-slate-300 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={(e) => { e.stopPropagation(); setConfirming(true); }}
                  className="w-8 h-8 rounded-full border border-slate-200 flex items-center justify-center text-slate-400 hover:border-red-300 hover:text-red-500 transition-colors"
                  title="Delete listing"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )
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
    </div>
  );
}
