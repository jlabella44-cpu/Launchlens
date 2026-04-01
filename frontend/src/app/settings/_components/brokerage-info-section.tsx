"use client";

import React, { useRef } from "react";

interface BrandKitFormState {
  brokerage_name: string;
  agent_name: string;
  primary_color: string;
  secondary_color: string;
  font_primary: string;
  logo_url: string | null;
  headshot_url: string | null;
  team_logo_url: string | null;
}

interface BrokerageInfoSectionProps {
  form: BrandKitFormState;
  setForm: React.Dispatch<React.SetStateAction<BrandKitFormState>>;
  onHeadshotUpload: (file: File) => void;
  headshotPreview: string | null;
  uploadingHeadshot: boolean;
}

export default function BrokerageInfoSection({
  form,
  setForm,
  onHeadshotUpload,
  headshotPreview,
  uploadingHeadshot,
}: BrokerageInfoSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const headshotSrc = headshotPreview || form.headshot_url;

  const inputClass =
    "w-full px-4 py-3 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm";

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
            d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21"
          />
        </svg>
        <h3
          className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Brokerage Info
        </h3>
      </div>

      {/* Name Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Brokerage Name
          </label>
          <input
            type="text"
            className={inputClass}
            value={form.brokerage_name}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, brokerage_name: e.target.value }))
            }
            placeholder="e.g. Apex Realty Group"
          />
        </div>
        <div>
          <label
            className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-1.5"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Agent Name
          </label>
          <input
            type="text"
            className={inputClass}
            value={form.agent_name}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, agent_name: e.target.value }))
            }
            placeholder="e.g. Jane Doe"
          />
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-white/10 my-6" />

      {/* Pilot Profile Image */}
      <div>
        <h4
          className="text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-4"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Pilot Profile Image
        </h4>
        <div className="flex items-center gap-4">
          {/* Preview */}
          <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-white/10 flex-shrink-0 bg-[var(--color-input-bg)] flex items-center justify-center">
            {headshotSrc ? (
              <img
                src={headshotSrc}
                alt="Headshot"
                className="w-full h-full object-cover"
              />
            ) : (
              <svg
                className="w-8 h-8 text-[var(--color-text)]/30"
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

          {/* Actions */}
          <div className="flex flex-col gap-2">
            <button
              type="button"
              disabled={uploadingHeadshot}
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 rounded-lg bg-[#0F1B2D] text-white text-xs font-medium hover:bg-[#0F1B2D]/80 transition-colors disabled:opacity-50"
            >
              {uploadingHeadshot ? "Uploading..." : "Upload Headshot"}
            </button>
            {headshotSrc && (
              <button
                type="button"
                onClick={() => {
                  setForm((prev) => ({ ...prev, headshot_url: null }));
                }}
                className="text-xs text-red-400 hover:text-red-300 transition-colors text-left"
              >
                Remove
              </button>
            )}
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onHeadshotUpload(file);
              e.target.value = "";
            }}
          />
        </div>
      </div>
    </section>
  );
}
