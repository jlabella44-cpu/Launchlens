"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";

export function Nav() {
  const { user, logout } = useAuth();

  return (
    <nav className="glass sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
      <Link
        href="/listings"
        className="font-[var(--font-heading)] text-xl font-bold text-[var(--color-primary)] tracking-wide"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        ListingJet
      </Link>

      <div className="flex items-center gap-4">
        {user && (
          <Link
            href="/review"
            className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
          >
            Review Queue
          </Link>
        )}
        <Link
          href="/pricing"
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
        >
          Pricing
        </Link>
        {user && (
          <Link
            href="/settings"
            className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
          >
            Settings
          </Link>
        )}
        {user && (
          <>
            <span className="text-sm text-[var(--color-text-secondary)]">
              {user.email}
            </span>
            <Button variant="secondary" onClick={logout}>
              Sign Out
            </Button>
          </>
        )}
      </div>
    </nav>
  );
}
