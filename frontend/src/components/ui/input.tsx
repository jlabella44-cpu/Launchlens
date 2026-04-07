"use client";

import { forwardRef, useId, type InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id: propId, ...props }, ref) => {
    const autoId = useId();
    const id = propId || autoId;
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={id} className="text-sm font-medium text-[var(--color-text)]">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={`px-3 py-2 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)]
            text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]
            focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50 focus:border-[var(--color-primary)]
            transition-all ${error ? "border-red-400" : ""} ${className}`}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          {...props}
        />
        {error && <p id={`${id}-error`} role="alert" className="text-xs text-red-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
