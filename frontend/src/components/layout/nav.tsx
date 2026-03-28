"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";

export function Nav() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="glass sticky top-0 z-50 px-4 sm:px-6 py-3">
      <div className="flex items-center justify-between">
        <Link
          href="/listings"
          className="font-[var(--font-heading)] text-xl font-bold text-[var(--color-primary)] tracking-wide"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          LaunchLens
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-4">
          <Link
            href="/pricing"
            className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors min-h-[44px] flex items-center"
          >
            Pricing
          </Link>
          {user && (
            <>
              <Link
                href="/billing"
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors min-h-[44px] flex items-center"
              >
                Billing
              </Link>
              <span className="text-sm text-[var(--color-text-secondary)] truncate max-w-[180px]">
                {user.email}
              </span>
              <Button variant="secondary" onClick={logout}>
                Sign Out
              </Button>
            </>
          )}
        </div>

        {/* Hamburger button (mobile) */}
        <button
          className="md:hidden min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-black/5 transition-colors touch-manipulation"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6 text-[var(--color-text)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden mt-3 pt-3 border-t border-[var(--color-border)] space-y-1">
          <Link
            href="/pricing"
            className="block px-3 py-3 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-black/5 rounded-lg transition-colors min-h-[44px] flex items-center touch-manipulation"
            onClick={() => setMenuOpen(false)}
          >
            Pricing
          </Link>
          {user && (
            <>
              <Link
                href="/billing"
                className="block px-3 py-3 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-black/5 rounded-lg transition-colors min-h-[44px] flex items-center touch-manipulation"
                onClick={() => setMenuOpen(false)}
              >
                Billing
              </Link>
              <Link
                href="/listings"
                className="block px-3 py-3 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-black/5 rounded-lg transition-colors min-h-[44px] flex items-center touch-manipulation"
                onClick={() => setMenuOpen(false)}
              >
                My Listings
              </Link>
              <div className="px-3 py-2 text-xs text-[var(--color-text-secondary)] truncate">
                {user.email}
              </div>
              <div className="px-3 pb-2">
                <Button variant="secondary" onClick={logout} className="w-full">
                  Sign Out
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
