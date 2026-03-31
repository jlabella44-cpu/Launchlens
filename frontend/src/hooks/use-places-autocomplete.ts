"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface PlacePrediction {
  description: string;
  place_id: string;
  structured_formatting: {
    main_text: string;
    secondary_text: string;
  };
}

interface AddressComponents {
  street: string;
  city: string;
  state: string;
  zip: string;
}

declare global {
  interface Window {
    google?: {
      maps: {
        places: {
          AutocompleteService: new () => {
            getPlacePredictions: (
              request: Record<string, unknown>,
              callback: (predictions: PlacePrediction[] | null, status: string) => void
            ) => void;
          };
          PlacesService: new (el: HTMLElement) => {
            getDetails: (
              request: Record<string, unknown>,
              callback: (place: Record<string, unknown> | null, status: string) => void
            ) => void;
          };
          PlacesServiceStatus: { OK: string };
        };
      };
      accounts?: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (element: HTMLElement, config: Record<string, unknown>) => void;
        };
      };
    };
  }
}

const GOOGLE_PLACES_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_PLACES_API_KEY;

let scriptLoaded = false;
let scriptLoading = false;
const loadCallbacks: (() => void)[] = [];

function loadGoogleMapsScript(): Promise<void> {
  if (scriptLoaded) return Promise.resolve();
  return new Promise((resolve) => {
    if (scriptLoading) {
      loadCallbacks.push(resolve);
      return;
    }
    scriptLoading = true;
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_PLACES_API_KEY}&libraries=places`;
    script.async = true;
    script.onload = () => {
      scriptLoaded = true;
      scriptLoading = false;
      resolve();
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    document.head.appendChild(script);
  });
}

export function usePlacesAutocomplete() {
  const [query, setQuery] = useState("");
  const [predictions, setPredictions] = useState<PlacePrediction[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const serviceRef = useRef<any>(null);
  const placesServiceRef = useRef<any>(null);
  const attrRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!GOOGLE_PLACES_API_KEY) return;
    loadGoogleMapsScript().then(() => {
      serviceRef.current = new window.google!.maps.places.AutocompleteService();
      // PlacesService needs a DOM element (can be hidden)
      const el = document.createElement("div");
      placesServiceRef.current = new window.google!.maps.places.PlacesService(el);
    });
  }, []);

  useEffect(() => {
    if (!query || query.length < 3 || !serviceRef.current) {
      setPredictions([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(() => {
      serviceRef.current!.getPlacePredictions(
        {
          input: query,
          types: ["address"],
          componentRestrictions: { country: "us" },
        },
        (results: PlacePrediction[] | null, status: string) => {
          if (status === window.google!.maps.places.PlacesServiceStatus.OK && results) {
            setPredictions(results);
            setIsOpen(true);
          } else {
            setPredictions([]);
            setIsOpen(false);
          }
        }
      );
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const selectPlace = useCallback(
    (placeId: string): Promise<AddressComponents> => {
      return new Promise((resolve) => {
        if (!placesServiceRef.current) {
          resolve({ street: query, city: "", state: "", zip: "" });
          return;
        }
        placesServiceRef.current.getDetails(
          { placeId, fields: ["address_components"] },
          (place: Record<string, unknown> | null, status: string) => {
            setIsOpen(false);
            setPredictions([]);
            if (status !== window.google!.maps.places.PlacesServiceStatus.OK || !place) {
              resolve({ street: query, city: "", state: "", zip: "" });
              return;
            }
            const components = place.address_components as Array<{
              long_name: string;
              short_name: string;
              types: string[];
            }>;
            const get = (type: string) =>
              components.find((c) => c.types.includes(type));

            const streetNumber = get("street_number")?.long_name || "";
            const route = get("route")?.long_name || "";
            const city =
              get("locality")?.long_name ||
              get("sublocality_level_1")?.long_name ||
              "";
            const state = get("administrative_area_level_1")?.short_name || "";
            const zip = get("postal_code")?.long_name || "";

            const street = [streetNumber, route].filter(Boolean).join(" ");
            setQuery(street);
            resolve({ street, city, state, zip });
          }
        );
      });
    },
    [query]
  );

  const dismiss = useCallback(() => {
    setIsOpen(false);
    setPredictions([]);
  }, []);

  return {
    query,
    setQuery,
    predictions,
    isOpen,
    selectPlace,
    dismiss,
    attrRef,
  };
}
