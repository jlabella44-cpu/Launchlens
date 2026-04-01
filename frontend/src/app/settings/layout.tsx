"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const tabs = [
    { href: "/settings", label: "Brand Kit" },
    { href: "/settings/team", label: "Team" },
  ];

  return (
    <div>
      {/* Tab bar rendered above child content */}
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-4">
        <div className="flex gap-1 border-b border-[var(--color-card-border)]">
          {tabs.map((tab) => {
            const isActive = tab.href === "/settings"
              ? pathname === "/settings"
              : pathname?.startsWith(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`px-5 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px ${
                  isActive
                    ? "border-[#F97316] text-[#F97316]"
                    : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
                }`}
                style={{ fontFamily: "var(--font-heading)" }}
              >
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>
      {children}
    </div>
  );
}
