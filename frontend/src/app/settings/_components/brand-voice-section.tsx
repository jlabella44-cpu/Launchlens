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
}

interface BrandVoiceSectionProps {
  form: BrandKitFormState;
  setForm: React.Dispatch<React.SetStateAction<BrandKitFormState>>;
}

const VOICE_OPTIONS = [
  { value: "", label: "Select a voice..." },
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "luxurious", label: "Luxurious" },
  { value: "casual", label: "Casual" },
  { value: "authoritative", label: "Authoritative" },
];

const TONE_OPTIONS = [
  { value: "", label: "Select a tone..." },
  { value: "warm", label: "Warm" },
  { value: "confident", label: "Confident" },
  { value: "exclusive", label: "Exclusive" },
  { value: "approachable", label: "Approachable" },
  { value: "bold", label: "Bold" },
];

export default function BrandVoiceSection({ form, setForm }: BrandVoiceSectionProps) {
  return (
    <section className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6 backdrop-blur-xl">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center">
          <svg className="w-4 h-4 text-[#0F1B2D]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <h2
          className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Brand Voice
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        {/* Voice */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Voice Style
          </label>
          <Select
            value={form.brand_voice}
            onChange={(e) => setForm((prev) => ({ ...prev, brand_voice: e.target.value }))}
            options={VOICE_OPTIONS}
          />
        </div>

        {/* Tone */}
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Tone
          </label>
          <Select
            value={form.brand_tone}
            onChange={(e) => setForm((prev) => ({ ...prev, brand_tone: e.target.value }))}
            options={TONE_OPTIONS}
          />
        </div>
      </div>

      {/* Voice Notes */}
      <div>
        <label
          className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-secondary)] mb-1.5"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Custom AI Instructions
        </label>
        <textarea
          value={form.voice_notes}
          onChange={(e) => setForm((prev) => ({ ...prev, voice_notes: e.target.value }))}
          placeholder="E.g., Always mention school district proximity, emphasize walkability scores, use metric measurements for international listings..."
          rows={3}
          className="w-full px-4 py-3 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm resize-none"
        />
        <p className="text-[10px] text-[var(--color-text-secondary)] mt-1">
          These instructions guide AI when generating listing descriptions and marketing copy.
        </p>
      </div>
    </section>
  );
}
