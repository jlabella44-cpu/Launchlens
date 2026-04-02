"use client";

import React, { useRef, useState, useCallback } from "react";

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

interface LogosSectionProps {
  form: BrandKitFormState;
  setForm: React.Dispatch<React.SetStateAction<BrandKitFormState>>;
  onBrokerageLogoUpload: (file: File) => void;
  onTeamLogoUpload: (file: File) => void;
  brokerageLogoPreview: string | null;
  teamLogoPreview: string | null;
  uploadingLogo: boolean;
  uploadingTeamLogo: boolean;
}

function LogoUploadArea({
  label,
  previewSrc,
  uploading,
  onUpload,
  onRemove,
}: {
  label: string;
  previewSrc: string | null;
  uploading: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file && file.type.startsWith("image/")) {
        onUpload(file);
      }
    },
    [onUpload]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  return (
    <div>
      <label
        className="block text-[10px] uppercase tracking-wider font-medium text-[var(--color-text)]/60 mb-3"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        {label}
      </label>

      {/* Drop Zone / Preview */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
        }}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onDragLeave={handleDragLeave}
        className={`
          w-[120px] h-[120px] rounded-xl overflow-hidden cursor-pointer
          flex items-center justify-center transition-all
          ${
            previewSrc
              ? "border-2 border-white/10"
              : `border-2 border-dashed ${
                  dragOver
                    ? "border-[#FF6B2C] bg-[#FF6B2C]/10"
                    : "border-white/20 hover:border-white/40"
                } bg-[var(--color-input-bg)]`
          }
        `}
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-1">
            <svg
              className="w-6 h-6 text-[#FF6B2C] animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <span className="text-[10px] text-[var(--color-text)]/40">
              Uploading...
            </span>
          </div>
        ) : previewSrc ? (
          <img
            src={previewSrc}
            alt={label}
            className="w-full h-full object-contain p-2"
          />
        ) : (
          <svg
            className="w-8 h-8 text-[var(--color-text)]/20"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
            />
          </svg>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-2">
        <button
          type="button"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
          className="text-xs text-[var(--color-text)]/60 hover:text-[var(--color-text)] transition-colors disabled:opacity-50"
        >
          Replace
        </button>
        {previewSrc && (
          <button
            type="button"
            onClick={onRemove}
            className="text-xs text-red-400 hover:text-red-300 transition-colors"
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
          if (file) onUpload(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}

export default function LogosSection({
  form,
  setForm,
  onBrokerageLogoUpload,
  onTeamLogoUpload,
  brokerageLogoPreview,
  teamLogoPreview,
  uploadingLogo,
  uploadingTeamLogo,
}: LogosSectionProps) {
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
            d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
          />
        </svg>
        <h3
          className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Logos
        </h3>
      </div>

      {/* Two-Column Logo Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <LogoUploadArea
          label="Brokerage Logo"
          previewSrc={brokerageLogoPreview || form.logo_url}
          uploading={uploadingLogo}
          onUpload={onBrokerageLogoUpload}
          onRemove={() => setForm((prev) => ({ ...prev, logo_url: null }))}
        />
        <LogoUploadArea
          label="Personal / Team Logo"
          previewSrc={teamLogoPreview || form.team_logo_url}
          uploading={uploadingTeamLogo}
          onUpload={onTeamLogoUpload}
          onRemove={() =>
            setForm((prev) => ({ ...prev, team_logo_url: null }))
          }
        />
      </div>
    </section>
  );
}
