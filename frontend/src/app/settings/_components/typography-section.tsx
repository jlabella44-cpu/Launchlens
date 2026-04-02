"use client";

import React from "react";
import { Select } from "@/components/ui/select";

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

interface TypographySectionProps {
  form: BrandKitFormState;
  setForm: React.Dispatch<React.SetStateAction<BrandKitFormState>>;
}

const FONT_OPTIONS = [
  "",
  "Cinzel",
  "Josefin Sans",
  "Playfair Display",
  "Montserrat",
  "Lato",
  "Roboto",
  "Open Sans",
  "Cormorant Garamond",
  "Raleway",
  "Poppins",
  "Inter",
  "DM Sans",
  "Libre Baskerville",
  "Source Sans Pro",
];

export default function TypographySection({
  form,
  setForm,
}: TypographySectionProps) {
  return (
    <section className="rounded-xl bg-[var(--color-surface)]/60 backdrop-blur-md border border-white/10 p-6 shadow-lg">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
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
            d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
          />
        </svg>
        <h3
          className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Typography
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {/* Heading Font */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Heading Font
          </label>
          <Select
            value={form.font_primary}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, font_primary: e.target.value }))
            }
            options={FONT_OPTIONS.map((font) => ({
              label: font || "Default (Exo 2)",
              value: font,
            }))}
          />
        </div>

        {/* Body Font */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Body Font
          </label>
          <Select
            value={form.font_secondary}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, font_secondary: e.target.value }))
            }
            options={FONT_OPTIONS.map((font) => ({
              label: font || "Default (Josefin Sans)",
              value: font,
            }))}
          />
        </div>
      </div>

      {/* Font Preview */}
      <div className="rounded-lg border border-white/10 bg-[var(--color-input-bg)] p-5">
        <p
          className="text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Preview
        </p>
        <p
          className="text-xl font-bold text-[var(--color-text)] mb-1"
          style={{ fontFamily: form.font_primary || "var(--font-heading)" }}
        >
          The Stratos Villa — $4,250,000
        </p>
        <p
          className="text-sm text-[var(--color-text-secondary)] leading-relaxed"
          style={{ fontFamily: form.font_secondary || "var(--font-body)" }}
        >
          Experience uncompromised altitude with this architectural marvel. Engineered for elite living with seamless glass transitions and panoramic views.
        </p>
      </div>
    </section>
  );
}
