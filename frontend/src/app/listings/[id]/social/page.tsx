"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { SocialPostHub } from "@/components/listings/social-post-hub";

function SocialPage() {
  const params = useParams();
  const id = params.id as string;

  useEffect(() => {
    document.title = "Social Post Hub | ListingJet";
  }, []);

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        {/* Back link */}
        <Link
          href={`/listings/${id}`}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Listing
        </Link>

        {/* Heading */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-[#F97316]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            <span className="text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-secondary)] font-semibold">
              Content Distribution
            </span>
          </div>
          <h1
            className="text-3xl sm:text-4xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Social Post Hub
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            Ready-to-post content for Instagram, Facebook, and TikTok.
          </p>
        </div>

        <SocialPostHub listingId={id} />

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-slate-100 dark:border-white/10 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-300">
          <span>ListingJet</span>
          <span>© {new Date().getFullYear()} ListingJet Command. All rights reserved.</span>
        </footer>
      </main>
    </>
  );
}

export default function SocialPostHubPage() {
  return (
    <ProtectedRoute>
      <SocialPage />
    </ProtectedRoute>
  );
}
