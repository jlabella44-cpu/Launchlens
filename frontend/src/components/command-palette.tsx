"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/auth-context";

interface CommandItem {
  id: string;
  label: string;
  section: string;
  href?: string;
  action?: () => void;
  shortcut?: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user, logout } = useAuth();

  const commands: CommandItem[] = [
    // Navigation
    { id: "dashboard", label: "Go to Dashboard", section: "Navigation", href: "/dashboard" },
    { id: "listings", label: "Go to Listings", section: "Navigation", href: "/listings" },
    { id: "analytics", label: "Go to Analytics", section: "Navigation", href: "/analytics" },
    { id: "billing", label: "Go to Billing", section: "Navigation", href: "/billing" },
    { id: "settings", label: "Go to Settings", section: "Navigation", href: "/settings" },
    { id: "pricing", label: "Go to Pricing", section: "Navigation", href: "/pricing" },
    { id: "brand-kit", label: "Go to Brand Kit", section: "Navigation", href: "/settings" },
    { id: "team", label: "Go to Team Settings", section: "Navigation", href: "/settings/team" },
    // Actions
    { id: "new-listing", label: "Create New Listing", section: "Actions", href: "/listings?new=1" },
    { id: "demo", label: "Try Demo", section: "Actions", href: "/demo" },
    // Legal
    { id: "privacy", label: "Privacy Policy", section: "Legal", href: "/privacy" },
    { id: "terms", label: "Terms of Service", section: "Legal", href: "/terms" },
    // Account
    ...(user
      ? [
          { id: "logout", label: "Sign Out", section: "Account", action: () => { logout(); setOpen(false); } },
        ]
      : [
          { id: "login", label: "Sign In", section: "Account", href: "/login" },
          { id: "register", label: "Create Account", section: "Account", href: "/register" },
        ]),
  ];

  // Admin commands
  if (user?.role === "superadmin" || user?.role === "admin") {
    commands.push(
      { id: "review", label: "Go to Review Queue", section: "Navigation", href: "/review" },
    );
  }
  if (user?.role === "superadmin") {
    commands.push(
      { id: "admin", label: "Go to Admin Panel", section: "Navigation", href: "/admin" },
    );
  }

  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  const sections = [...new Set(filtered.map((c) => c.section))];

  const execute = useCallback(
    (item: CommandItem) => {
      setOpen(false);
      setQuery("");
      if (item.action) {
        item.action();
      } else if (item.href) {
        router.push(item.href);
      }
    },
    [router]
  );

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Arrow key navigation
  useEffect(() => {
    if (!open) return;
    function handleNav(e: KeyboardEvent) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        execute(filtered[selectedIndex]);
      }
    }
    document.addEventListener("keydown", handleNav);
    return () => document.removeEventListener("keydown", handleNav);
  }, [open, filtered, selectedIndex, execute]);

  // Reset selection when query changes
  useEffect(() => { setSelectedIndex(0); }, [query]);

  // Focus trap
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first?.focus();

    function handleTab(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }
    dialog.addEventListener("keydown", handleTab);
    return () => dialog.removeEventListener("keydown", handleTab);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[200]"
          onClick={() => setOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

          {/* Dialog */}
          <div className="relative flex justify-center pt-[20vh]" onClick={(e) => e.stopPropagation()}>
            <motion.div
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-label="Command palette"
              initial={{ opacity: 0, y: -16, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -16, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
            >
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
            <svg className="w-5 h-5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands..."
              className="flex-1 text-sm bg-transparent outline-none text-[var(--color-text)] placeholder:text-slate-400"
            />
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-medium text-slate-400 bg-slate-100 rounded border border-slate-200">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-[300px] overflow-y-auto py-2">
            {filtered.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-slate-400">No results found</p>
            )}
            {sections.map((section) => (
              <div key={section}>
                <p className="px-4 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {section}
                </p>
                {filtered
                  .filter((c) => c.section === section)
                  .map((item) => {
                    const globalIndex = filtered.indexOf(item);
                    return (
                      <button
                        key={item.id}
                        onClick={() => execute(item)}
                        className={`w-full flex items-center justify-between px-4 py-2 text-sm text-left transition-colors ${
                          globalIndex === selectedIndex
                            ? "bg-[#F97316]/10 text-[#F97316]"
                            : "text-[var(--color-text)] hover:bg-slate-50"
                        }`}
                      >
                        <span>{item.label}</span>
                        {item.shortcut && (
                          <kbd className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                            {item.shortcut}
                          </kbd>
                        )}
                      </button>
                    );
                  })}
              </div>
            ))}
          </div>

          {/* Footer hint */}
          <div className="border-t border-slate-100 px-4 py-2 flex items-center gap-4 text-[10px] text-slate-400">
            <span><kbd className="font-medium">↑↓</kbd> navigate</span>
            <span><kbd className="font-medium">↵</kbd> select</span>
            <span><kbd className="font-medium">esc</kbd> close</span>
          </div>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
