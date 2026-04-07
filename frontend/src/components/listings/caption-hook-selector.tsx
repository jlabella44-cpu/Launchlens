"use client";

import { useState, useEffect } from "react";

export type CaptionStyle =
  | "storyteller"
  | "data-driven"
  | "luxury_minimalist"
  | "urgency"
  | "lifestyle";

const CAPTION_STYLES: { key: CaptionStyle; label: string }[] = [
  { key: "storyteller", label: "Storyteller" },
  { key: "data-driven", label: "Data-Driven" },
  { key: "luxury_minimalist", label: "Luxury" },
  { key: "urgency", label: "Urgency" },
  { key: "lifestyle", label: "Lifestyle" },
];

interface CaptionHookSelectorProps {
  captions: Partial<Record<CaptionStyle, string>>;
  platform: string;
  listingId: string;
  onSelect: (style: CaptionStyle, text: string) => void;
}

const storageKey = (listingId: string, platform: string) =>
  `lj_caption_style_${listingId}_${platform}`;

export function CaptionHookSelector({
  captions,
  platform,
  listingId,
  onSelect,
}: CaptionHookSelectorProps) {
  const [selected, setSelected] = useState<CaptionStyle>("storyteller");

  // Restore persisted selection
  useEffect(() => {
    const stored = localStorage.getItem(storageKey(listingId, platform)) as CaptionStyle | null;
    if (stored && captions[stored] !== undefined) {
      setSelected(stored);
    }
  }, [listingId, platform, captions]);

  // Notify parent on mount + on change
  useEffect(() => {
    const text = captions[selected] ?? "";
    onSelect(selected, text);
  }, [selected, captions, onSelect]);

  function handleSelect(style: CaptionStyle) {
    setSelected(style);
    localStorage.setItem(storageKey(listingId, platform), style);
  }

  const availableStyles = CAPTION_STYLES.filter((s) => captions[s.key] !== undefined);
  if (availableStyles.length === 0) return null;

  return (
    <div className="space-y-2">
      {/* Tab row */}
      <div className="flex flex-wrap gap-1">
        {availableStyles.map((s) => (
          <button
            key={s.key}
            onClick={() => handleSelect(s.key)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors focus:outline-none ${
              selected === s.key
                ? "bg-[#F97316] text-white"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Caption text */}
      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
        {captions[selected] ?? "No caption available for this style."}
      </p>
    </div>
  );
}
