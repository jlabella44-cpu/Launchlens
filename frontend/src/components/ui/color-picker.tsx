"use client";

interface ColorPickerProps {
  label: string;
  value: string;
  onChange: (color: string) => void;
}

export function ColorPicker({ label, value, onChange }: ColorPickerProps) {
  const colorId = `color-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={colorId} className="text-sm font-medium text-[var(--color-text)]">
        {label}
      </label>
      <div className="flex items-center gap-3">
        <input
          id={colorId}
          type="color"
          value={value || "#000000"}
          onChange={(e) => onChange(e.target.value)}
          className="w-10 h-10 rounded-lg border border-white/20 cursor-pointer bg-transparent"
          aria-label={`${label} color picker`}
        />
        <input
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#000000"
          maxLength={7}
          aria-label={`${label} hex value`}
          className="px-3 py-2 rounded-lg border border-white/20 bg-white/60 backdrop-blur-sm
            text-[var(--color-text)] text-sm font-mono w-28
            focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50"
        />
      </div>
    </div>
  );
}
