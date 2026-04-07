"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { AddressAutocomplete } from "@/components/ui/address-autocomplete";
import { GlassCard } from "@/components/ui/glass-card";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
}

const PROPERTY_TYPES = [
  "Single Family",
  "Condo/Townhouse",
  "Multi-Family",
  "Land/Lot",
  "Commercial",
];

const INPUT_CLASS =
  "w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm";

export function StepPropertyDetails({ formData, onUpdate, onNext }: Props) {
  const { toast } = useToast();
  const [lookingUp, setLookingUp] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const { address, metadata } = formData;

  function setAddress(updates: Partial<WizardFormData["address"]>) {
    onUpdate({ address: { ...address, ...updates } });
  }

  function setMeta(updates: Partial<WizardFormData["metadata"]>) {
    onUpdate({ metadata: { ...metadata, ...updates } });
  }

  const lookupProperty = useCallback(
    async (addr: { street: string; city: string; state: string; zip: string }) => {
      const fullAddress = `${addr.street}, ${addr.city}, ${addr.state} ${addr.zip}`;
      setLookingUp(true);
      try {
        const data = await apiClient.propertyLookup(fullAddress);
        if (data.found && data.core) {
          const updates: Partial<WizardFormData["metadata"]> = {};
          if (data.core.beds) updates.beds = data.core.beds;
          if (data.core.baths) updates.baths = data.core.baths;
          if (data.core.sqft) updates.sqft = data.core.sqft;
          if (data.details?.property_type) updates.property_type = data.details.property_type;
          onUpdate({ metadata: { ...metadata, ...updates } });
          toast("Property details auto-filled from ATTOM", "success");
        }
      } catch {
        // ATTOM lookup failed — user can fill manually
      } finally {
        setLookingUp(false);
      }
    },
    [metadata, onUpdate, toast]
  );

  async function handleNext() {
    setError("");

    if (!address.street || !address.city || !address.state) {
      setError("Street address, city, and state are required.");
      return;
    }
    if (!metadata.beds || !metadata.baths || !metadata.sqft || !metadata.price) {
      setError("Beds, baths, square footage, and price are required.");
      return;
    }

    // If we already created the listing (e.g. user went back), just advance
    if (formData.listingId) {
      onNext();
      return;
    }

    setCreating(true);
    try {
      const listing = await apiClient.createListing({
        address: {
          street: address.street,
          city: address.city,
          state: address.state,
          zip: address.zip,
          unit: address.unit || undefined,
        } as any,
        metadata: {
          beds: metadata.beds,
          baths: metadata.baths,
          sqft: metadata.sqft,
          price: metadata.price,
          property_type: metadata.property_type || undefined,
        } as any,
      });
      onUpdate({ listingId: listing.id });
      onNext();
    } catch (err: any) {
      setError(err?.message || "Failed to create listing. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <GlassCard tilt={false}>
      <h2
        className="text-xl font-bold mb-6"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Property Details
      </h2>

      <div className="space-y-5">
        {/* Street Address */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Street Address <span className="text-red-500">*</span>
          </label>
          <AddressAutocomplete
            value={address.street}
            onChange={(val) => setAddress({ street: val })}
            onAddressSelect={(addr) => {
              setAddress({
                street: addr.street,
                city: addr.city,
                state: addr.state,
                zip: addr.zip,
              });
              lookupProperty(addr);
            }}
          />
          {lookingUp && (
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 animate-pulse">
              Looking up property details...
            </p>
          )}
        </div>

        {/* Unit */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Unit <span className="text-[var(--color-text-secondary)] font-normal">(optional)</span>
          </label>
          <input
            value={address.unit}
            onChange={(e) => setAddress({ unit: e.target.value })}
            placeholder="Apt 4B"
            className={INPUT_CLASS}
          />
        </div>

        {/* City / State / ZIP */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              City <span className="text-red-500">*</span>
            </label>
            <input
              value={address.city}
              onChange={(e) => setAddress({ city: e.target.value })}
              required
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              State <span className="text-red-500">*</span>
            </label>
            <input
              value={address.state}
              onChange={(e) => setAddress({ state: e.target.value })}
              placeholder="TX"
              required
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">ZIP</label>
            <input
              value={address.zip}
              onChange={(e) => setAddress({ zip: e.target.value })}
              placeholder="78701"
              className={INPUT_CLASS}
            />
          </div>
        </div>

        {/* Property Type */}
        <div>
          <label className="block text-sm font-medium mb-1">Property Type</label>
          <select
            value={metadata.property_type}
            onChange={(e) => setMeta({ property_type: e.target.value })}
            className={INPUT_CLASS}
          >
            <option value="">Select type...</option>
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Beds / Baths / Sqft / Price */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Beds <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={metadata.beds ?? ""}
              onChange={(e) =>
                setMeta({ beds: e.target.value ? Number(e.target.value) : null })
              }
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Baths <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="0"
              step="0.5"
              value={metadata.baths ?? ""}
              onChange={(e) =>
                setMeta({ baths: e.target.value ? Number(e.target.value) : null })
              }
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Sqft <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={metadata.sqft ?? ""}
              onChange={(e) =>
                setMeta({ sqft: e.target.value ? Number(e.target.value) : null })
              }
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Price <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={metadata.price ?? ""}
              onChange={(e) =>
                setMeta({ price: e.target.value ? Number(e.target.value) : null })
              }
              className={INPUT_CLASS}
            />
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
        )}

        <div className="flex justify-end pt-2">
          <Button onClick={handleNext} loading={creating}>
            Next: Upload Photos
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}
