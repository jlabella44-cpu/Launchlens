"use client";

import { useState, useEffect } from "react";

const SHORTCUTS = [
  { keys: ["⌘", "K"], description: "Open command palette" },
  { keys: ["?"], description: "Show keyboard shortcuts" },
  { keys: ["G", "D"], description: "Go to Dashboard" },
  { keys: ["G", "L"], description: "Go to Listings" },
  { keys: ["G", "A"], description: "Go to Analytics" },
  { keys: ["G", "S"], description: "Go to Settings" },
  { keys: ["G", "B"], description: "Go to Billing" },
];

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (
        e.key === "?" &&
        !e.metaKey &&
        !e.ctrlKey &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200]" onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative flex justify-center pt-[15vh]" onClick={(e) => e.stopPropagation()}>
        <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2
              className="text-lg font-semibold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Keyboard Shortcuts
            </h2>
          </div>
          <div className="px-5 py-3 space-y-2">
            {SHORTCUTS.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-[var(--color-text-secondary)]">{s.description}</span>
                <div className="flex items-center gap-1">
                  {s.keys.map((key, j) => (
                    <kbd
                      key={j}
                      className="min-w-[24px] px-1.5 py-0.5 text-center text-xs font-medium text-slate-500 bg-slate-100 rounded border border-slate-200"
                    >
                      {key}
                    </kbd>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="px-5 py-3 border-t border-slate-100">
            <p className="text-[10px] text-slate-400 text-center">
              Press <kbd className="px-1 py-0.5 bg-slate-100 rounded border border-slate-200 text-[10px]">ESC</kbd> to close
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
