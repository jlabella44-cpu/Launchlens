"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { useBranding } from "@/contexts/branding-context";

export function Nav() {
  const { user, logout } = useAuth();
  const branding = useBranding();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);

  const linkClass = (href: string) => {
    const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
    return isActive
      ? "text-sm font-semibold text-[var(--color-primary)] border-b-2 border-[var(--color-cta)] pb-0.5 transition-colors"
      : "text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors";
  };

  return (
    <nav className="glass sticky top-0 z-50 px-6 py-3">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="font-[var(--font-heading)] text-xl font-bold text-[var(--color-primary)] tracking-wide shrink-0"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          {branding.logoUrl ? (
            <img src={branding.logoUrl} alt={branding.appName} className="h-7" />
          ) : (
            branding.appName
          )}
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
          {user && <Link href="/dashboard" className={linkClass("/dashboard")}>Dashboard</Link>}
          {user && <Link href="/listings" className={linkClass("/listings")}>Listings</Link>}
          {user && <Link href="/analytics" className={linkClass("/analytics")}>Analytics</Link>}
          {user && <Link href="/analytics/performance" className={linkClass("/analytics/performance")}>Performance</Link>}
          {user && <Link href="/health" className={linkClass("/health")}>Health</Link>}
          {user && (user.role === "admin" || user.role === "superadmin") && (
            <Link href="/review" className={linkClass("/review")}>Review</Link>
          )}
          {user && <Link href="/billing" className={linkClass("/billing")}>Billing</Link>}
          <Link href="/pricing" className={linkClass("/pricing")}>Pricing</Link>
          <Link href="/demo" className={linkClass("/demo")}>Demo</Link>
          <Link href="/faq" className={linkClass("/faq")}>FAQ</Link>
          {user && <Link href="/support" className={linkClass("/support")}>Support</Link>}
          {user && <Link href="/settings" className={linkClass("/settings")}>Settings</Link>}
          {user && user.role === "superadmin" && (
            <Link href="/admin" className="text-sm font-semibold text-[var(--color-primary)] hover:text-[var(--color-primary)]/80 transition-colors">
              Admin
            </Link>
          )}
          {user && (
            <NotificationBell
              open={bellOpen}
              onToggle={() => setBellOpen((v) => !v)}
              onClose={() => setBellOpen(false)}
            />
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
          {user && <Link href="/dashboard" className={linkClass("/dashboard")} onClick={() => setMenuOpen(false)}>Dashboard</Link>}
          {user && <Link href="/listings" className={linkClass("/listings")} onClick={() => setMenuOpen(false)}>Listings</Link>}
          {user && <Link href="/analytics" className={linkClass("/analytics")} onClick={() => setMenuOpen(false)}>Analytics</Link>}
          {user && <Link href="/health" className={linkClass("/health")} onClick={() => setMenuOpen(false)}>Health</Link>}
          {user && (user.role === "admin" || user.role === "superadmin") && (
            <Link href="/review" className={linkClass("/review")} onClick={() => setMenuOpen(false)}>Review</Link>
          )}
          {user && <Link href="/billing" className={linkClass("/billing")} onClick={() => setMenuOpen(false)}>Billing</Link>}
          <Link href="/pricing" className={linkClass("/pricing")} onClick={() => setMenuOpen(false)}>Pricing</Link>
          <Link href="/demo" className={linkClass("/demo")} onClick={() => setMenuOpen(false)}>Demo</Link>
          <Link href="/faq" className={linkClass("/faq")} onClick={() => setMenuOpen(false)}>FAQ</Link>
          {user && <Link href="/support" className={linkClass("/support")} onClick={() => setMenuOpen(false)}>Support</Link>}
          {user && <Link href="/settings" className={linkClass("/settings")} onClick={() => setMenuOpen(false)}>Settings</Link>}
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
