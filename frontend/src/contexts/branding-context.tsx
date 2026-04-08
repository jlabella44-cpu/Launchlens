"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface Branding {
  appName: string;
  tagline: string;
  logoUrl: string | null;
  faviconUrl: string | null;
  primaryColor: string;
  secondaryColor: string;
  fontPrimary: string | null;
  brokerageName: string | null;
  poweredByVisible: boolean;
  whiteLabelEnabled: boolean;
}

const DEFAULT_BRANDING: Branding = {
  appName: "ListingJet",
  tagline: "From raw listing media to launch-ready marketing in minutes",
  logoUrl: null,
  faviconUrl: null,
  primaryColor: "#2563EB",
  secondaryColor: "#F97316",
  fontPrimary: null,
  brokerageName: null,
  poweredByVisible: false,
  whiteLabelEnabled: false,
};

const BrandingContext = createContext<Branding>(DEFAULT_BRANDING);

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>(DEFAULT_BRANDING);

  useEffect(() => {
    fetch("/api/branding")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          setBranding({
            appName: data.app_name || DEFAULT_BRANDING.appName,
            tagline: data.tagline || DEFAULT_BRANDING.tagline,
            logoUrl: data.logo_url,
            faviconUrl: data.favicon_url,
            primaryColor: data.primary_color || DEFAULT_BRANDING.primaryColor,
            secondaryColor: data.secondary_color || DEFAULT_BRANDING.secondaryColor,
            fontPrimary: data.font_primary,
            brokerageName: data.brokerage_name,
            poweredByVisible: data.powered_by_visible ?? false,
            whiteLabelEnabled: data.white_label_enabled ?? false,
          });

          // Apply CSS custom properties for dynamic theming
          const root = document.documentElement;
          if (data.primary_color) root.style.setProperty("--color-primary", data.primary_color);
          if (data.secondary_color) root.style.setProperty("--color-cta", data.secondary_color);

          // Update page title
          if (data.white_label_enabled && data.app_name) {
            document.title = data.app_name;
          }

          // Update favicon
          if (data.favicon_url) {
            const link = document.querySelector("link[rel='icon']") as HTMLLinkElement | null;
            if (link) link.href = data.favicon_url;
          }
        }
      })
      .catch(() => {});
  }, []);

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
