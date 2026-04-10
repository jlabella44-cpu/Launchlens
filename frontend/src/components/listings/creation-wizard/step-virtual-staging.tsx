"use client";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepVirtualStaging({ formData, onUpdate, onNext, onBack }: Props) {
  const { uploadedAssets, stagingAssetIds, selectedAddons } = formData;

  function toggleAsset(id: string) {
    const isSelected = stagingAssetIds.includes(id);
    const nextIds = isSelected
      ? stagingAssetIds.filter((x) => x !== id)
      : [...stagingAssetIds, id];

    // Auto-sync virtual_staging addon
    const hasStaging = nextIds.length > 0;
    const nextAddons = hasStaging
      ? selectedAddons.includes("virtual_staging")
        ? selectedAddons
        : [...selectedAddons, "virtual_staging"]
      : selectedAddons.filter((a) => a !== "virtual_staging");

    onUpdate({ stagingAssetIds: nextIds, selectedAddons: nextAddons });
  }

  function handleSkip() {
    // Clear any staging selections
    const nextAddons = selectedAddons.filter((a) => a !== "virtual_staging");
    onUpdate({ stagingAssetIds: [], selectedAddons: nextAddons });
    onNext();
  }

  return (
    <GlassCard tilt={false}>
      <div className="flex items-baseline gap-2 mb-2">
        <h2
          className="text-xl font-bold"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Virtual Staging
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold px-1.5 py-0.5 rounded-full border border-[var(--color-border)]">
          Optional
        </span>
      </div>
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        Select photos you&apos;d like virtually staged, or skip this step to
        continue without staging. Each selected photo will have furniture and
        decor added by AI.
      </p>

      {uploadedAssets.length === 0 ? (
        <div className="py-12 text-center text-[var(--color-text-secondary)]">
          <p className="text-sm">No photos uploaded yet.</p>
        </div>
      ) : (
        <>
          {stagingAssetIds.length > 0 && (
            <div className="mb-4 px-3 py-2 rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] text-sm font-medium inline-flex items-center gap-2">
              <span>
                {stagingAssetIds.length} room{stagingAssetIds.length !== 1 ? "s" : ""} selected
                for staging
              </span>
              <span className="text-xs font-normal opacity-70">· 15 credits</span>
            </div>
          )}

          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {uploadedAssets.map((asset) => {
              const selected = stagingAssetIds.includes(asset.id);
              return (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => toggleAsset(asset.id)}
                  className={`
                    relative aspect-square rounded-xl overflow-hidden cursor-pointer
                    transition-all duration-150
                    focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]
                    ${selected
                      ? "ring-2 ring-[var(--color-primary)] scale-[0.97]"
                      : "hover:scale-[0.98] hover:ring-1 hover:ring-[var(--color-border)]"
                    }
                  `}
                >
                  {asset.url ? (
                    <img
                      src={asset.url}
                      alt={asset.filename}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-slate-100 flex items-center justify-center">
                      <svg
                        className="w-6 h-6 text-slate-400"
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

                  {/* Selected overlay */}
                  {selected && (
                    <div className="absolute inset-0 bg-[var(--color-primary)]/20 flex items-start justify-end p-1.5">
                      <div className="w-5 h-5 rounded-full bg-[var(--color-primary)] flex items-center justify-center shadow">
                        <svg
                          className="w-3 h-3 text-white"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={3}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-8 pt-4 border-t border-[var(--color-border)]">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={handleSkip}>
            Skip
          </Button>
          <Button onClick={onNext}>
            Next: Add-ons
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}
