"use client";

import { useRouter } from "next/navigation";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import type { ListingResponse } from "@/lib/types";

interface ListingCardProps {
  listing: ListingResponse;
}

export function ListingCard({ listing }: ListingCardProps) {
  const router = useRouter();
  const { address, metadata, state } = listing;

  const price = metadata.price
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(metadata.price)
    : null;

  return (
    <GlassCard
      onClick={() => router.push(`/listings/${listing.id}`)}
      className="group"
    >
      <div className="flex items-start justify-between mb-3">
        <h3
          className="text-lg font-semibold text-[var(--color-text)] group-hover:text-[var(--color-primary)] transition-colors truncate"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          {address.street || "New Listing"}
        </h3>
        <Badge state={state} />
      </div>

      {(address.city || address.state) && (
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          {[address.city, address.state].filter(Boolean).join(", ")}
        </p>
      )}

      <div className="flex items-center gap-4 text-sm text-[var(--color-text-secondary)]">
        {metadata.beds != null && (
          <span>{metadata.beds} bed{metadata.beds !== 1 ? "s" : ""}</span>
        )}
        {metadata.baths != null && (
          <span>{metadata.baths} bath{metadata.baths !== 1 ? "s" : ""}</span>
        )}
        {metadata.sqft != null && (
          <span>{metadata.sqft.toLocaleString()} sqft</span>
        )}
      </div>

      {price && (
        <p className="mt-3 text-xl font-bold text-[var(--color-primary)]">
          {price}
        </p>
      )}
    </GlassCard>
  );
}
