"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import type { PropertyLookupResponse } from "@/lib/api-client";

interface AddressLookupProps {
  onAddressSelected: (address: { street: string; city: string; state: string; zip: string }) => void;
  onPropertyData: (data: PropertyLookupResponse) => void;
  initialAddress?: { street: string; city: string; state: string; zip: string };
}

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
  "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
  "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
  "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
];

const inputClass =
  "w-full rounded-md bg-zinc-800/50 border border-zinc-700 text-white px-3 py-2 text-sm " +
  "placeholder:text-zinc-500 focus:outline-none focus:border-amber-500 transition-colors";

const labelClass = "block text-xs font-medium text-zinc-400 mb-1";

export function AddressLookup({ onAddressSelected, onPropertyData, initialAddress }: AddressLookupProps) {
  const [isNewConstruction, setIsNewConstruction] = useState(false);
  const [street, setStreet] = useState(initialAddress?.street ?? "");
  const [city, setCity] = useState(initialAddress?.city ?? "");
  const [state, setState] = useState(initialAddress?.state ?? "");
  const [zip, setZip] = useState(initialAddress?.zip ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streetInputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const googleLoadedRef = useRef(false);

  const triggerLookup = useCallback(
    async (fullAddress: string, parsed: { street: string; city: string; state: string; zip: string }) => {
      if (isNewConstruction) return;
      setLoading(true);
      setError(null);
      onAddressSelected(parsed);
      try {
        const data = await apiClient.propertyLookup(fullAddress);
        onPropertyData(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Property lookup failed";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [isNewConstruction, onAddressSelected, onPropertyData]
  );

  // Initialize Google Places Autocomplete
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !window.google?.maps?.places ||
      !streetInputRef.current ||
      googleLoadedRef.current
    ) {
      return;
    }

    googleLoadedRef.current = true;

    const autocomplete = new window.google.maps.places.Autocomplete(streetInputRef.current, {
      types: ["address"],
      componentRestrictions: { country: "us" },
      fields: ["address_components", "formatted_address"],
    });

    autocompleteRef.current = autocomplete;

    autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();
      if (!place.address_components) return;

      let newStreet = "";
      let newCity = "";
      let newState = "";
      let newZip = "";
      let streetNumber = "";
      let route = "";

      for (const component of place.address_components) {
        const types = component.types;
        if (types.includes("street_number")) streetNumber = component.long_name;
        else if (types.includes("route")) route = component.long_name;
        else if (types.includes("locality")) newCity = component.long_name;
        else if (types.includes("administrative_area_level_1")) newState = component.short_name;
        else if (types.includes("postal_code")) newZip = component.long_name;
      }

      newStreet = [streetNumber, route].filter(Boolean).join(" ");

      setStreet(newStreet);
      setCity(newCity);
      setState(newState);
      setZip(newZip);

      const parsed = { street: newStreet, city: newCity, state: newState, zip: newZip };
      const fullAddress = place.formatted_address ?? `${newStreet}, ${newCity}, ${newState} ${newZip}`;
      triggerLookup(fullAddress, parsed);
    });

    return () => {
      if (autocompleteRef.current) {
        window.google.maps.event.clearInstanceListeners(autocompleteRef.current);
        autocompleteRef.current = null;
        googleLoadedRef.current = false;
      }
    };
  }, [triggerLookup]);

  // Manual lookup triggered by blur on zip (last field)
  const handleManualLookup = () => {
    if (!street || !city || !state || !zip) return;
    const parsed = { street, city, state, zip };
    const fullAddress = `${street}, ${city}, ${state} ${zip}`;
    triggerLookup(fullAddress, parsed);
  };

  return (
    <div className="space-y-4">
      {/* New Construction Toggle */}
      <label className="flex items-center gap-3 cursor-pointer group select-none">
        <div
          className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
            isNewConstruction ? "bg-amber-500" : "bg-zinc-700"
          }`}
          onClick={() => setIsNewConstruction((v) => !v)}
          role="checkbox"
          aria-checked={isNewConstruction}
          tabIndex={0}
          onKeyDown={(e) => e.key === " " && setIsNewConstruction((v) => !v)}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
              isNewConstruction ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </div>
        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
          Never Listed / New Construction
        </span>
      </label>

      {/* Street */}
      <div>
        <label className={labelClass}>Street Address</label>
        <input
          ref={streetInputRef}
          type="text"
          value={street}
          onChange={(e) => setStreet(e.target.value)}
          placeholder="123 Main St"
          className={inputClass}
          autoComplete="street-address"
        />
      </div>

      {/* City / State / Zip */}
      <div className="grid grid-cols-6 gap-3">
        <div className="col-span-3">
          <label className={labelClass}>City</label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Austin"
            className={inputClass}
            autoComplete="address-level2"
          />
        </div>

        <div className="col-span-1">
          <label className={labelClass}>State</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className={`${inputClass} appearance-none`}
          >
            <option value="">--</option>
            {US_STATES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="col-span-2">
          <label className={labelClass}>ZIP Code</label>
          <input
            type="text"
            value={zip}
            onChange={(e) => setZip(e.target.value)}
            onBlur={handleManualLookup}
            placeholder="78701"
            maxLength={10}
            className={inputClass}
            autoComplete="postal-code"
          />
        </div>
      </div>

      {/* Status */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <svg
            className="animate-spin h-4 w-4 text-amber-500"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Looking up property data…
        </div>
      )}

      {error && !loading && (
        <p className="text-xs text-red-400">{error}</p>
      )}

      {isNewConstruction && (
        <p className="text-xs text-zinc-500 italic">
          Property lookup skipped for new construction / never-listed addresses.
        </p>
      )}
    </div>
  );
}

export default AddressLookup;
