"use client";

import React from "react";
import { motion } from "framer-motion";

interface BrandKitFormState {
  brokerage_name: string;
  agent_name: string;
  primary_color: string;
  secondary_color: string;
  font_primary: string;
  logo_url: string | null;
  headshot_url: string | null;
  team_logo_url: string | null;
  accent_color: string;
  background_color: string;
  font_secondary: string;
  brand_voice: string;
  brand_tone: string;
  voice_notes: string;
  voiceover_enabled: boolean;
}

interface HudPreviewProps {
  form: BrandKitFormState;
  brokerageLogoPreview: string | null;
  headshotPreview: string | null;
  teamLogoPreview: string | null;
  saving: boolean;
  saved: boolean;
  onSave: () => void;
}

export default function HudPreview({
  form,
  brokerageLogoPreview,
  headshotPreview,
  teamLogoPreview,
  saving,
  saved,
  onSave,
}: HudPreviewProps) {
  const brokerageLogo = brokerageLogoPreview || form.logo_url;
  const teamLogo = teamLogoPreview || form.team_logo_url;
  const headshot = headshotPreview || form.headshot_url;
  const accentColor = form.secondary_color || "#FF6B2C";

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <svg
          className="w-5 h-5 text-[#FF6B2C]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.348 14.652a3.75 3.75 0 0 1 0-5.304m5.304 0a3.75 3.75 0 0 1 0 5.304m-7.425 2.121a6.75 6.75 0 0 1 0-9.546m9.546 0a6.75 6.75 0 0 1 0 9.546M5.106 18.894c-3.808-3.807-3.808-9.98 0-13.788m13.788 0c3.808 3.807 3.808 9.98 0 13.788M12 12h.008v.008H12V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
          />
        </svg>
        <h3
          className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Live HUD Preview
        </h3>
      </div>

      {/* Listing Card Preview */}
      <div className="rounded-xl overflow-hidden bg-[var(--color-surface)]/60 backdrop-blur-md border border-white/10 shadow-lg">
        {/* Property Image */}
        <div className="relative aspect-[4/3] bg-[#1a2744]">
          <img
            src="/images/listing-villa.jpg"
            alt="The Stratos Villa"
            className="w-full h-full object-cover"
          />

          {/* Brokerage Logo Overlay - Top Left */}
          {brokerageLogo && (
            <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm rounded-full px-3 py-1.5 shadow-md">
              <img
                src={brokerageLogo}
                alt="Brokerage"
                className="h-6 w-auto object-contain"
              />
            </div>
          )}

          {/* Team Logo Badge - Bottom Left */}
          {teamLogo && (
            <div className="absolute bottom-3 left-3 w-10 h-10 rounded-lg bg-white/90 backdrop-blur-sm shadow-md flex items-center justify-center overflow-hidden">
              <img
                src={teamLogo}
                alt="Team"
                className="w-8 h-8 object-contain"
              />
            </div>
          )}

          {/* Price Badge - Top Right */}
          <div
            className="absolute top-3 right-3 px-3 py-1.5 rounded-lg text-white text-sm font-bold shadow-md"
            style={{ backgroundColor: accentColor }}
          >
            $4,750,000
          </div>
        </div>

        {/* Card Content */}
        <div className="p-5">
          {/* Title */}
          <h4
            className="text-lg font-bold text-[var(--color-text)] mb-1"
            style={{ fontFamily: form.font_primary || "var(--font-heading)" }}
          >
            The Stratos Villa
          </h4>

          {/* Address */}
          <p className="text-xs text-[var(--color-text)]/50 mb-3">
            742 Aurelia Way, Los Angeles
          </p>

          {/* Status Badge */}
          <span
            className="inline-block px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-semibold text-white mb-4"
            style={{ backgroundColor: accentColor }}
          >
            Supersonic
          </span>

          {/* Specs Row */}
          <div className="flex items-center gap-4 text-xs text-[var(--color-text)]/60 mb-4">
            <div className="flex items-center gap-1.5">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.25 12l8.954-8.955a1.126 1.126 0 0 1 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
                />
              </svg>
              <span>5 beds</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                />
              </svg>
              <span>4.5 baths</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9m11.25-6v4.5m0-4.5h-4.5m4.5 0L15 9m-11.25 11.25v-4.5m0 4.5h4.5m-4.5 0L9 15m11.25 6v-4.5m0 4.5h-4.5m4.5 0L15 15"
                />
              </svg>
              <span>5,400 sqft</span>
            </div>
          </div>

          {/* Description */}
          <p
            className="text-xs text-[var(--color-text)]/50 leading-relaxed mb-4"
            style={{ fontFamily: form.font_primary || "var(--font-body)" }}
          >
            An architectural masterpiece with panoramic views, infinity pool, and
            private helipad. Designed for those who live life at altitude.
          </p>

          {/* Divider */}
          <div className="border-t border-white/10 my-4" />

          {/* Listed By */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full overflow-hidden border border-white/10 bg-[var(--color-input-bg)] flex items-center justify-center flex-shrink-0">
              {headshot ? (
                <img
                  src={headshot}
                  alt="Agent"
                  className="w-full h-full object-cover"
                />
              ) : (
                <svg
                  className="w-5 h-5 text-[var(--color-text)]/30"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
                  />
                </svg>
              )}
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[var(--color-text)]/40">
                Listed By
              </p>
              <p className="text-sm font-medium text-[var(--color-text)]">
                {form.agent_name || "Agent Name"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="w-full mt-6 px-6 py-3.5 rounded-full bg-[#FF6B2C] hover:bg-[#FF6B2C]/90 text-white font-semibold text-sm transition-all disabled:opacity-50 shadow-lg shadow-[#FF6B2C]/20"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        {saving ? "Saving..." : "Save Brand Kit"}
      </button>

      {/* Saved Message */}
      {saved && (
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="text-center text-xs text-green-400 mt-3 font-medium"
        >
          Brand kit saved successfully
        </motion.p>
      )}

      {/* Footer */}
      <p
        className="text-center text-[10px] uppercase tracking-wider text-[var(--color-text)]/30 mt-4"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Flight Check: All Systems Nominal
      </p>
    </div>
  );
}
