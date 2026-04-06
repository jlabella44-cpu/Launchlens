"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { usePlan } from "@/contexts/plan-context";
import apiClient from "@/lib/api-client";
import { trackEvent, AnalyticsEvents } from "@/lib/analytics";

type Mode = "mls" | "marketing";

const MODE_INFO: Record<Mode, { title: string; badge: string; items: { label: string; desc: string }[] }> = {
  mls: {
    title: "MLS Bundle Contents",
    badge: "UNBRANDED PREVIEW",
    items: [
      { label: "Unbranded Photos", desc: "24 professionally edited JPGs" },
      { label: "MLS Description", desc: "Plain text optimized for local boards" },
      { label: "Standard Resolution", desc: "Compressed to 2048px maximum width" },
    ],
  },
  marketing: {
    title: "Marketing Bundle Contents",
    badge: "BRANDED PREVIEW",
    items: [
      { label: "Branded Photos", desc: "24 photos with watermark & logo overlay" },
      { label: "Marketing Description", desc: "Dual-tone luxury & SEO-optimized copy" },
      { label: "Branded Flyer PDF", desc: "Print-ready A4 property flyer" },
      { label: "Social Media Posts", desc: "Platform-optimized captions & hashtags" },
      { label: "High Resolution", desc: "Full 4K resolution exports" },
    ],
  },
};

function ExportPage() {
  const params = useParams();
  const id = params.id as string;
  const { tier } = usePlan();
  const isFreeTier = !tier || tier === "free" || tier === "starter";
  useEffect(() => { document.title = "Export | ListingJet"; }, []);

  const [mode, setMode] = useState<Mode>("mls");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setError("");
    setDownloading(true);
    try {
      const res = await apiClient.getExport(id, mode);
      trackEvent(AnalyticsEvents.FIRST_EXPORT, { listing_id: id, mode, tier: tier || "free" });
      window.open(res.download_url, "_blank");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Export not available yet");
    } finally {
      setDownloading(false);
    }
  }

  const info = MODE_INFO[mode];

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-8">
        {/* Back Link */}
        <Link
          href={`/listings/${id}`}
          className="text-xs uppercase tracking-wider text-slate-400 hover:text-[#F97316] transition-colors mb-6 inline-flex items-center gap-1"
        >
          ← Back to Listing Detail
        </Link>

        {/* Header */}
        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold mb-1">
          System Export
        </p>
        <div className="flex items-center justify-between mb-8">
          <h1
            className="text-3xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Export Package
          </h1>

          {/* Toggle */}
          <div className="flex rounded-full border border-slate-200 p-0.5">
            {(["mls", "marketing"] as const).map((m) => (
              <motion.button
                key={m}
                onClick={() => setMode(m)}
                className={`px-5 py-2 rounded-full text-sm font-medium transition-colors cursor-pointer ${
                  mode === m
                    ? "bg-[#0B1120] text-white"
                    : "text-slate-400 hover:text-slate-600"
                }`}
                whileTap={{ scale: 0.97 }}
              >
                {m === "mls" ? "MLS" : "Marketing"}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Bundle Card */}
        <div className="bg-white rounded-2xl border border-slate-100 p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-6">
            {/* Preview Thumbnails */}
            <div className="flex-shrink-0">
              <div className="w-48 h-36 rounded-xl bg-gradient-to-br from-slate-200 to-slate-100 flex items-center justify-center">
                <svg className="w-10 h-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="flex gap-2 mt-2">
                {[1, 2].map((i) => (
                  <div key={i} className="w-14 h-10 rounded-lg bg-slate-100" />
                ))}
                <div className="w-14 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-xs text-slate-400 font-medium">
                  +24
                </div>
              </div>
            </div>

            {/* Bundle Contents */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-[#F97316]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <h3 className="font-semibold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
                  {info.title}
                </h3>
                <span className="text-[9px] uppercase tracking-wider font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                  {info.badge}
                </span>
              </div>

              <ul className="space-y-2.5">
                {info.items.map((item) => (
                  <li key={item.label} className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-[#F97316] mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <div>
                      <p className="text-sm font-medium text-[var(--color-text)]">{item.label}</p>
                      <p className="text-xs text-slate-400">{item.desc}</p>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-4">
                Branded Assets · {mode === "mls" ? "Standard" : "4K"} Resolution Exports
              </div>
            </div>
          </div>

          {/* File Info */}
          <div className="flex items-center gap-8 mt-6 pt-4 border-t border-slate-100">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-400">Total Size</p>
              <p className="text-lg font-bold text-[var(--color-text)]">84.2 MB</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-400">Format</p>
              <p className="text-lg font-bold text-[var(--color-text)]">ZIP</p>
            </div>
          </div>
        </div>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        {/* Download Button */}
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="w-full py-4 px-6 rounded-full bg-[#0B1120] hover:bg-[#1a2744] text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {downloading ? (
            <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <>
              Download Package
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </>
          )}
        </button>

        {/* Free-tier watermark notice */}
        {isFreeTier && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800">
                Exports include &ldquo;Powered by ListingJet&rdquo; watermark
              </p>
              <p className="text-xs text-amber-600 mt-1">
                Upgrade to any paid plan to remove watermarks and unlock full white-label branding.
              </p>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#F97316] hover:text-[#EA580C] mt-2 transition-colors"
              >
                View plans →
              </Link>
            </div>
          </div>
        )}

        {/* Status Footer */}
        <p className="text-center text-[10px] text-slate-400 uppercase tracking-wider mt-4">
          Package generated: Today at {new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })} · System Status: <span className="text-[#F97316]">Supersonic</span>
        </p>
      </main>
    </>
  );
}

export default function ExportPageWrapper() {
  return (
    <ProtectedRoute>
      <ExportPage />
    </ProtectedRoute>
  );
}
