"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { usePlan } from "@/contexts/plan-context";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onBack: () => void;
  onConfirm: () => void;
  submitting: boolean;
}

const ADDON_META: Record<string, { label: string; credits: number }> = {
  ai_video_tour: { label: "AI Video Tour", credits: 20 },
  virtual_staging: { label: "Virtual Staging", credits: 15 },
  "3d_floorplan": { label: "3D Floorplan", credits: 8 },
};

const BASE_CREDITS = 15;
const BUNDLE_CREDITS = 30;

const BASE_INCLUDED = [
  "Social content",
  "Social cuts",
  "Compliance check",
  "MLS package",
  "Property microsite",
];

export function StepReviewConfirm({
  formData,
  onBack,
  onConfirm,
  submitting,
}: Props) {
  const { creditBalance } = usePlan();
  const { address, metadata, uploadedAssets, stagingAssetIds, selectedAddons, useBundle } =
    formData;

  // Credit cost
  const addonCost = useBundle
    ? BUNDLE_CREDITS
    : selectedAddons.reduce((sum, id) => {
        return sum + (ADDON_META[id]?.credits ?? 0);
      }, 0);
  const totalCredits = BASE_CREDITS + addonCost;

  const canAfford =
    creditBalance !== null ? creditBalance >= totalCredits : true;

  const fullAddress = [
    address.street,
    address.unit,
    address.city,
    address.state,
    address.zip,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <GlassCard tilt={false}>
      <h2
        className="text-xl font-bold mb-6"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Review &amp; Confirm
      </h2>

      <div className="space-y-6">
        {/* Property summary */}
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)] mb-2">
            Property
          </h3>
          <div className="rounded-xl border border-[var(--color-border)] p-4 space-y-1">
            <p className="font-medium text-sm">{fullAddress || "—"}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {[
                metadata.property_type,
                metadata.beds != null ? `${metadata.beds} bd` : null,
                metadata.baths != null ? `${metadata.baths} ba` : null,
                metadata.sqft != null
                  ? `${metadata.sqft.toLocaleString()} sqft`
                  : null,
                metadata.price != null
                  ? `$${metadata.price.toLocaleString()}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
        </section>

        {/* Photo summary */}
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)] mb-2">
            Photos ({uploadedAssets.length})
          </h3>
          {uploadedAssets.length > 0 ? (
            <div className="flex gap-1.5 flex-wrap">
              {uploadedAssets.slice(0, 8).map((asset) => (
                <div
                  key={asset.id}
                  className="w-14 h-14 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0"
                >
                  {asset.url ? (
                    <img
                      src={asset.url}
                      alt={asset.filename}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg
                        className="w-4 h-4 text-slate-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
              {uploadedAssets.length > 8 && (
                <div className="w-14 h-14 rounded-lg bg-slate-100 flex items-center justify-center text-xs text-slate-500 font-medium flex-shrink-0">
                  +{uploadedAssets.length - 8}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-secondary)]">No photos uploaded.</p>
          )}

          {stagingAssetIds.length > 0 && (
            <p className="text-xs text-[var(--color-text-secondary)] mt-2">
              {stagingAssetIds.length} room{stagingAssetIds.length !== 1 ? "s" : ""} selected
              for virtual staging
            </p>
          )}
        </section>

        {/* Credit breakdown */}
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)] mb-2">
            Cost Breakdown
          </h3>
          <div className="rounded-xl border border-[var(--color-border)] p-4 space-y-2">
            {/* Base */}
            <div className="flex justify-between text-sm">
              <span>Base listing</span>
              <span className="font-medium">{BASE_CREDITS} credits</span>
            </div>

            {/* Included in base */}
            <div className="pl-3 border-l-2 border-[var(--color-border)] space-y-0.5 pb-1">
              {BASE_INCLUDED.map((item) => (
                <p key={item} className="text-xs text-[var(--color-text-secondary)]">
                  ✓ {item}
                </p>
              ))}
            </div>

            {/* Add-ons */}
            {useBundle ? (
              <div className="flex justify-between text-sm pt-1">
                <span>Premium Bundle</span>
                <span className="font-medium">{BUNDLE_CREDITS} credits</span>
              </div>
            ) : (
              selectedAddons.map((id) => {
                const meta = ADDON_META[id];
                if (!meta) return null;
                return (
                  <div key={id} className="flex justify-between text-sm">
                    <span>{meta.label}</span>
                    <span className="font-medium">{meta.credits} credits</span>
                  </div>
                );
              })
            )}

            {/* Total */}
            <div className="flex justify-between text-sm font-bold pt-2 border-t border-[var(--color-border)]">
              <span>Total</span>
              <span className="text-[var(--color-primary)]">{totalCredits} credits</span>
            </div>

            {/* Balance */}
            {creditBalance !== null && (
              <div className="flex justify-between text-xs text-[var(--color-text-secondary)] pt-1">
                <span>Your balance</span>
                <span
                  className={
                    canAfford ? "text-green-600 font-medium" : "text-red-600 font-medium"
                  }
                >
                  {creditBalance} credits
                </span>
              </div>
            )}
          </div>

          {!canAfford && (
            <div className="mt-3 px-4 py-3 rounded-lg bg-red-50 border border-red-200">
              <p className="text-sm text-red-700">
                Insufficient credits.{" "}
                <Link
                  href="/billing/credits"
                  className="underline font-medium"
                >
                  Purchase more credits
                </Link>{" "}
                to continue.
              </p>
            </div>
          )}
        </section>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-8 pt-4 border-t border-[var(--color-border)]">
        <Button variant="secondary" onClick={onBack} disabled={submitting}>
          Back
        </Button>
        <Button
          onClick={onConfirm}
          loading={submitting}
          disabled={!canAfford}
        >
          {submitting ? "Creating…" : `Confirm & Create (${totalCredits} credits)`}
        </Button>
      </div>
    </GlassCard>
  );
}
