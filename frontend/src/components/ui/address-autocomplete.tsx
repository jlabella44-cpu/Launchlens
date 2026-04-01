"use client";

import { useRef, useEffect } from "react";
import { usePlacesAutocomplete } from "@/hooks/use-places-autocomplete";

interface ParsedAddress {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface AddressAutocompleteProps {
  onAddressSelect: (address: ParsedAddress) => void;
  className?: string;
  /** Current value for the street input (controlled) */
  value?: string;
  /** Called when the user types (before selecting a place) */
  onChange?: (value: string) => void;
}

/**
 * Google Places address autocomplete input.
 * Requires NEXT_PUBLIC_GOOGLE_PLACES_API_KEY with the Places API enabled.
 * Falls back to a plain text input if the API key is not configured.
 */
export function AddressAutocomplete({
  onAddressSelect,
  className = "",
  value,
  onChange,
}: AddressAutocompleteProps) {
  const places = usePlacesAutocomplete();
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        places.dismiss();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [places]);

  return (
    <div className="relative" ref={dropdownRef}>
      <input
        value={places.query || value || ""}
        onChange={(e) => {
          places.setQuery(e.target.value);
          onChange?.(e.target.value);
        }}
        onFocus={() => {
          if (places.predictions.length > 0) places.setQuery(places.query);
        }}
        className={`w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white
          focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]
          placeholder:text-[var(--color-text-secondary)] ${className}`}
        placeholder="Start typing an address..."
        autoComplete="off"
      />
      {places.isOpen && places.predictions.length > 0 && (
        <div className="absolute z-50 top-full mt-1 w-full bg-white border border-[var(--color-border)] rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {places.predictions.map((p) => (
            <button
              key={p.place_id}
              type="button"
              className="w-full text-left px-4 py-2.5 text-sm hover:bg-[var(--color-primary)]/10 transition-colors cursor-pointer"
              onClick={async () => {
                const addr = await places.selectPlace(p.place_id);
                onAddressSelect(addr);
              }}
            >
              <span className="font-medium">{p.structured_formatting.main_text}</span>
              <span className="text-[var(--color-text-secondary)] ml-1">
                {p.structured_formatting.secondary_text}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
