"use client";

import React from "react";
import { ColorPicker } from "@/components/ui/color-picker";

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
}

interface BrandColorsSectionProps {
  form: BrandKitFormState;
  setForm: React.Dispatch<React.SetStateAction<BrandKitFormState>>;
}

export default function BrandColorsSection({
  form,
  setForm,
}: BrandColorsSectionProps) {
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
            d="M4.098 19.902a3.75 3.75 0 0 0 5.304 0l6.401-6.402M6.75 21A3.75 3.75 0 0 1 3 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125V11.25a2.25 2.25 0 0 1-2.25 2.25H6.75Zm0 0h.008v.008H6.75V21Zm9-14.25h.008v.008H15.75V6.75Z"
          />
        </svg>
        <h3
          className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Brand Colors
        </h3>
      </div>

      {/* Color Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Primary Color */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Primary Mach Navy
          </label>
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-full shadow-lg border-2 border-white/10 flex-shrink-0"
              style={{ backgroundColor: form.primary_color || "#0F1B2D" }}
            />
            <ColorPicker
              label=""
              value={form.primary_color}
              onChange={(color: string) =>
                setForm((prev) => ({ ...prev, primary_color: color }))
              }
            />
          </div>
        </div>

        {/* Secondary Color */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Afterburner Accent
          </label>
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-full shadow-lg border-2 border-white/10 flex-shrink-0"
              style={{ backgroundColor: form.secondary_color || "#FF6B2C" }}
            />
            <ColorPicker
              label=""
              value={form.secondary_color}
              onChange={(color: string) =>
                setForm((prev) => ({ ...prev, secondary_color: color }))
              }
            />
          </div>
        </div>
      </div>

      {/* Row 2: Accent + Background */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-6 pt-6 border-t border-[var(--color-card-border)]">
        {/* Accent Color */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Accent Highlight
          </label>
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-full shadow-lg border-2 border-white/10 flex-shrink-0"
              style={{ backgroundColor: form.accent_color || "#3B82F6" }}
            />
            <ColorPicker
              label=""
              value={form.accent_color || "#3B82F6"}
              onChange={(color: string) =>
                setForm((prev) => ({ ...prev, accent_color: color }))
              }
            />
          </div>
        </div>

        {/* Background Color */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Background Base
          </label>
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-full shadow-lg border-2 border-white/10 flex-shrink-0"
              style={{ backgroundColor: form.background_color || "#F8FAFC" }}
            />
            <ColorPicker
              label=""
              value={form.background_color || "#F8FAFC"}
              onChange={(color: string) =>
                setForm((prev) => ({ ...prev, background_color: color }))
              }
            />
          </div>
        </div>
      </div>
    </section>
  );
}
