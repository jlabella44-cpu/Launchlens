"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export function Nav() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const linkClass = "text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors";

  return (
    <nav className="glass sticky top-0 z-50 px-6 py-3">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="font-[var(--font-heading)] text-xl font-bold text-[var(--color-primary)] tracking-wide shrink-0"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          ListingJet
        </Link>

        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden w-8 h-8 flex items-center justify-center text-[var(--color-text-secondary)]"
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>

        <div className="hidden md:flex items-center gap-4">
          {user && <Link href="/dashboard" className={linkClass}>Dashboard</Link>}
          {user && <Link href="/listings" className={linkClass}>Listings</Link>}
          {user && (user.role === "admin" || user.role === "superadmin") && (
            <Link href="/review" className={linkClass}>Review</Link>
          )}
          {user && <Link href="/billing" className={linkClass}>Billing</Link>}
          <Link href="/pricing" className={linkClass}>Pricing</Link>
          <Link href="/demo" className={linkClass}>Demo</Link>
          {user && <Link href="/settings" className={linkClass}>Settings</Link>}
          {user && user.role === "superadmin" && (
            <Link href="/admin" className="text-sm font-semibold text-[var(--color-primary)] hover:text-[var(--color-primary)]/80 transition-colors">
              Admin
            </Link>
          )}
          <ThemeToggle />
          {user && (
            <>
              <span className="text-sm text-[var(--color-text-secondary)]">{user.email}</span>
              <Button variant="secondary" onClick={logout}>Sign Out</Button>
            </>
          )}
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden mt-3 pt-3 border-t border-slate-200/50 flex flex-col gap-3">
          {user && <Link href="/dashboard" className={linkClass} onClick={() => setMenuOpen(false)}>Dashboard</Link>}
          {user && <Link href="/listings" className={linkClass} onClick={() => setMenuOpen(false)}>Listings</Link>}
          {user && (user.role === "admin" || user.role === "superadmin") && (
            <Link href="/review" className={linkClass} onClick={() => setMenuOpen(false)}>Review</Link>
          )}
          {user && <Link href="/billing" className={linkClass} onClick={() => setMenuOpen(false)}>Billing</Link>}
          <Link href="/pricing" className={linkClass} onClick={() => setMenuOpen(false)}>Pricing</Link>
          <Link href="/demo" className={linkClass} onClick={() => setMenuOpen(false)}>Demo</Link>
          {user && <Link href="/settings" className={linkClass} onClick={() => setMenuOpen(false)}>Settings</Link>}
          {user && user.role === "superadmin" && (
            <Link href="/admin" className="text-sm font-semibold text-[var(--color-primary)]" onClick={() => setMenuOpen(false)}>Admin</Link>
          )}
          <div className="flex items-center gap-3 pt-2">
            <ThemeToggle />
            {user && (
              <>
                <span className="text-sm text-[var(--color-text-secondary)] truncate">{user.email}</span>
                <Button variant="secondary" onClick={logout}>Sign Out</Button>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
