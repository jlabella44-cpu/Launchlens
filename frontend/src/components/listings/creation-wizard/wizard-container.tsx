"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { usePlan } from "@/contexts/plan-context";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import { StepPropertyDetails } from "./step-property-details";
import { StepUploadPhotos } from "./step-upload-photos";
import { StepVirtualStaging } from "./step-virtual-staging";
import { StepAddons } from "./step-addons";
import { StepReviewConfirm } from "./step-review-confirm";

export interface WizardFormData {
  // Step 1: Property Details
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    unit: string;
  };
  metadata: {
    beds: number | null;
    baths: number | null;
    sqft: number | null;
    price: number | null;
    property_type: string;
  };
  // Step 2: Photos
  listingId: string | null;
  uploadedAssets: Array<{ id: string; filename: string; url: string }>;
  // Step 3: Virtual Staging
  stagingAssetIds: string[];
  // Step 4: Add-ons
  selectedAddons: string[];
  useBundle: boolean;
}

const INITIAL_FORM_DATA: WizardFormData = {
  address: { street: "", city: "", state: "", zip: "", unit: "" },
  metadata: { beds: null, baths: null, sqft: null, price: null, property_type: "" },
  listingId: null,
  uploadedAssets: [],
  stagingAssetIds: [],
  selectedAddons: [],
  useBundle: false,
};

const WIZARD_STORAGE_KEY = "listingjet_wizard_draft_v1";

interface PersistedWizardState {
  formData: WizardFormData;
  step: number;
}

function loadPersistedState(): PersistedWizardState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(WIZARD_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedWizardState;
    if (!parsed?.formData?.listingId) return null;
    return parsed;
  } catch {
    return null;
  }
}

const STEPS = [
  { label: "Property Details", number: 1 },
  { label: "Upload Photos", number: 2 },
  { label: "Virtual Staging", number: 3 },
  { label: "Add-ons", number: 4 },
  { label: "Review & Confirm", number: 5 },
];

export function WizardContainer() {
  const [hydrated, setHydrated] = useState(false);
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<WizardFormData>(INITIAL_FORM_DATA);
  const [submitting, setSubmitting] = useState(false);
  const [creditBlock, setCreditBlock] = useState<{ message: string } | null>(null);
  const [resumed, setResumed] = useState(false);
  const router = useRouter();
  const { billingModel, canAffordListing, creditBalance, listingCreditCost, refresh } = usePlan();
  const { toast } = useToast();

  // Hydrate from localStorage once on mount (only if a persisted listingId exists)
  useEffect(() => {
    const persisted = loadPersistedState();
    if (persisted) {
      setFormData(persisted.formData);
      setStep(persisted.step);
      setResumed(true);
    }
    setHydrated(true);
  }, []);

  // Persist whenever the wizard has a listingId (i.e., after step 1 created the listing).
  // Skip until we've finished hydrating so we don't overwrite on first paint.
  useEffect(() => {
    if (!hydrated) return;
    if (typeof window === "undefined") return;
    if (formData.listingId) {
      try {
        window.localStorage.setItem(
          WIZARD_STORAGE_KEY,
          JSON.stringify({ formData, step }),
        );
      } catch {
        // quota or serialization failure — best-effort only
      }
    }
  }, [hydrated, formData, step]);

  const clearPersistedWizard = useCallback(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(WIZARD_STORAGE_KEY);
    } catch {
      // best effort
    }
  }, []);

  const showCreditWarning = billingModel === "credit" && !canAffordListing;

  const updateFormData = useCallback((updates: Partial<WizardFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  }, []);

  const goNext = useCallback(() => setStep((s) => Math.min(s + 1, 5)), []);
  const goBack = useCallback(() => setStep((s) => Math.max(s - 1, 1)), []);

  const handleConfirm = useCallback(async () => {
    if (!formData.listingId) return;
    setSubmitting(true);
    try {
      // Set staging tags if any
      if (formData.stagingAssetIds.length > 0) {
        await apiClient.setStagingTags(formData.listingId, formData.stagingAssetIds);
      }

      // Start pipeline with selected addons
      const addons = formData.useBundle ? ["all_addons_bundle"] : formData.selectedAddons;
      const result = await apiClient.startPipeline(formData.listingId, addons);

      await refresh();
      clearPersistedWizard();
      toast(
        `Listing created! ${result.credits_deducted} credits deducted. Processing has begun.`,
        "success"
      );
      router.push(`/listings/${formData.listingId}`);
    } catch (err: any) {
      if (err?.status === 402) {
        setCreditBlock({ message: err?.message || "Insufficient credits." });
      } else {
        toast(err?.message || "Failed to start pipeline", "error");
      }
    } finally {
      setSubmitting(false);
    }
  }, [formData, refresh, toast, router, clearPersistedWizard]);

  const handleStartOver = useCallback(() => {
    clearPersistedWizard();
    setFormData(INITIAL_FORM_DATA);
    setStep(1);
    setResumed(false);
  }, [clearPersistedWizard]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {resumed && (
        <div className="mb-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-[var(--color-text)]">
              Resumed your draft
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1">
              We kept your property details, uploaded photos, and add-on selections from last time.
            </p>
          </div>
          <button
            type="button"
            onClick={handleStartOver}
            className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] transition-colors"
          >
            Start over
          </button>
        </div>
      )}

      {/* Insufficient credits warning */}
      {showCreditWarning && (
        <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">
            Insufficient credits ({creditBalance} remaining, {listingCreditCost} needed)
          </p>
          <p className="text-xs text-amber-600 mt-1">
            You can still fill out the details, but you&apos;ll need to purchase credits before submitting.
          </p>
          <a
            href="/billing"
            className="inline-block mt-2 px-4 py-1.5 rounded-full bg-amber-500 text-white text-xs font-semibold hover:bg-amber-600 transition-colors"
          >
            Buy Credits
          </a>
        </div>
      )}

      {/* Step indicator */}
      <nav className="flex items-center justify-between mb-8">
        {STEPS.map((s) => (
          <div key={s.number} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                s.number === step
                  ? "bg-[var(--color-primary)] text-white"
                  : s.number < step
                    ? "bg-[var(--color-primary)]/20 text-[var(--color-primary)]"
                    : "bg-[var(--color-surface)] text-[var(--color-text-secondary)]"
              }`}
            >
              {s.number < step ? "\u2713" : s.number}
            </div>
            <span
              className={`text-sm hidden sm:inline ${
                s.number === step
                  ? "text-[var(--color-text)] font-medium"
                  : "text-[var(--color-text-secondary)]"
              }`}
            >
              {s.label}
            </span>
            {s.number < STEPS.length && (
              <div className="w-8 h-px bg-[var(--color-border)] hidden sm:block" />
            )}
          </div>
        ))}
      </nav>

      {/* Step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {step === 1 && (
            <StepPropertyDetails
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
            />
          )}
          {step === 2 && (
            <StepUploadPhotos
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 3 && (
            <StepVirtualStaging
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 4 && (
            <StepAddons
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 5 && (
            <StepReviewConfirm
              formData={formData}
              onUpdate={updateFormData}
              onBack={goBack}
              onConfirm={handleConfirm}
              submitting={submitting}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {creditBlock && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="credit-block-title"
        >
          <div className="w-full max-w-md rounded-2xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-xl p-6">
            <h2 id="credit-block-title" className="text-lg font-semibold text-[var(--color-text)]">
              Not enough credits to start processing
            </h2>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
              {creditBlock.message}
            </p>
            <div className="mt-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-3">
              <p className="text-sm font-medium text-[var(--color-text)]">
                Your draft is saved.
              </p>
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                Your property details, uploaded photos, and add-on selections are safe.
                Top up your credits and return here — nothing you&apos;ve entered will be lost.
              </p>
            </div>
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setCreditBlock(null)}
                className="px-4 py-2 rounded-full text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] transition-colors"
              >
                Keep editing
              </button>
              <a
                href="/billing"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 rounded-full bg-[var(--color-primary)] text-white text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                Buy credits
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
