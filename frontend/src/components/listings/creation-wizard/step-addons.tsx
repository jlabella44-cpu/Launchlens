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

const INDIVIDUAL_ADDONS = [
  {
    id: "ai_video_tour",
    label: "AI Video Tour",
    description: "Cinematic walkthrough video generated from your photos",
    credits: 20,
    icon: "🎬",
  },
  {
    id: "virtual_staging",
    label: "Virtual Staging",
    description: "AI-furnished rooms for selected photos",
    credits: 15,
    icon: "🛋️",
  },
  {
    id: "3d_floorplan",
    label: "3D Floorplan",
    description: "Interactive 3D floorplan generated from listing data",
    credits: 8,
    icon: "📐",
  },
] as const;

const BUNDLE_CREDITS = 30;
const BUNDLE_FULL_PRICE = INDIVIDUAL_ADDONS.reduce((s, a) => s + a.credits, 0); // 43
const BUNDLE_SAVINGS = BUNDLE_FULL_PRICE - BUNDLE_CREDITS; // 13

export function StepAddons({ formData, onUpdate, onNext, onBack }: Props) {
  const { selectedAddons, useBundle } = formData;

  function toggleBundle() {
    if (useBundle) {
      onUpdate({ useBundle: false, selectedAddons: [] });
    } else {
      onUpdate({
        useBundle: true,
        selectedAddons: INDIVIDUAL_ADDONS.map((a) => a.id),
      });
    }
  }

  function toggleAddon(id: string) {
    // Selecting an individual addon deselects the bundle
    const next = selectedAddons.includes(id)
      ? selectedAddons.filter((a) => a !== id)
      : [...selectedAddons, id];

    // Check if all three are now selected — auto-promote to bundle
    const allSelected = INDIVIDUAL_ADDONS.every((a) => next.includes(a.id));
    onUpdate({
      selectedAddons: next,
      useBundle: allSelected,
    });
  }

  // Cost calculation
  const addonCost = useBundle
    ? BUNDLE_CREDITS
    : selectedAddons.reduce((sum, id) => {
        const addon = INDIVIDUAL_ADDONS.find((a) => a.id === id);
        return sum + (addon?.credits ?? 0);
      }, 0);

  const totalCost = 15 + addonCost; // base listing is always 15

  return (
    <GlassCard tilt={false}>
      <h2
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Add-ons
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        Your base listing (15 credits) already includes social content, social cuts,
        compliance check, MLS package, and a property microsite.
      </p>

      {/* Bundle card */}
      <button
        type="button"
        onClick={toggleBundle}
        className={`
          w-full text-left rounded-xl border-2 p-4 mb-4 transition-all duration-150 cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]
          ${
            useBundle
              ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
              : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50"
          }
        `}
      >
        <div className="flex items-start gap-3">
          <div
            className={`
              mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              transition-colors
              ${useBundle
                ? "border-[var(--color-primary)] bg-[var(--color-primary)]"
                : "border-[var(--color-border)]"
              }
            `}
          >
            {useBundle && (
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-sm">Premium Bundle</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">
                Save {BUNDLE_SAVINGS} credits
              </span>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              All 3 add-ons: AI Video Tour + Virtual Staging + 3D Floorplan
            </p>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="font-bold text-[var(--color-primary)]">{BUNDLE_CREDITS} credits</div>
            <div className="text-xs text-[var(--color-text-secondary)] line-through">
              {BUNDLE_FULL_PRICE} credits
            </div>
          </div>
        </div>
      </button>

      {/* Individual addon cards */}
      <div className="space-y-3">
        {INDIVIDUAL_ADDONS.map((addon) => {
          const checked = selectedAddons.includes(addon.id);
          return (
            <button
              key={addon.id}
              type="button"
              onClick={() => toggleAddon(addon.id)}
              disabled={useBundle}
              className={`
                w-full text-left rounded-xl border-2 p-4 transition-all duration-150 cursor-pointer
                focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]
                ${useBundle ? "opacity-60 cursor-not-allowed" : ""}
                ${
                  checked && !useBundle
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
                    : useBundle && checked
                    ? "border-[var(--color-primary)]/40 bg-[var(--color-primary)]/5"
                    : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50"
                }
              `}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`
                    w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0
                    transition-colors
                    ${checked
                      ? "border-[var(--color-primary)] bg-[var(--color-primary)]"
                      : "border-[var(--color-border)]"
                    }
                  `}
                >
                  {checked && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-lg">{addon.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{addon.label}</div>
                  <div className="text-xs text-[var(--color-text-secondary)] truncate">
                    {addon.description}
                  </div>
                </div>
                <div className="text-sm font-semibold text-[var(--color-primary)] flex-shrink-0">
                  {addon.credits} credits
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Cost summary */}
      <div className="mt-6 pt-4 border-t border-[var(--color-border)] space-y-1.5">
        <div className="flex justify-between text-sm text-[var(--color-text-secondary)]">
          <span>Base listing</span>
          <span>15 credits</span>
        </div>
        {addonCost > 0 && (
          <div className="flex justify-between text-sm text-[var(--color-text-secondary)]">
            <span>{useBundle ? "Premium Bundle" : "Add-ons"}</span>
            <span>{addonCost} credits</span>
          </div>
        )}
        <div className="flex justify-between text-sm font-bold pt-1 border-t border-[var(--color-border)]">
          <span>Total</span>
          <span className="text-[var(--color-primary)]">{totalCost} credits</span>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-6 pt-4 border-t border-[var(--color-border)]">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>
          Next: Review
        </Button>
      </div>
    </GlassCard>
  );
}
