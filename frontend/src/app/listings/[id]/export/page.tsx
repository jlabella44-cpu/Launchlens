"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

type Mode = "mls" | "marketing";

const MODE_INFO: Record<Mode, { title: string; items: string[] }> = {
  mls: {
    title: "MLS Package",
    items: [
      "Unbranded photos (MLS-compliant)",
      "MLS-safe description",
      "Standard resolution",
    ],
  },
  marketing: {
    title: "Marketing Package",
    items: [
      "Branded photos with watermark",
      "Marketing description (dual-tone)",
      "Branded flyer PDF",
      "Social media posts",
      "High resolution",
    ],
  },
};

function ExportPage() {
  const params = useParams();
  const id = params.id as string;
  const [mode, setMode] = useState<Mode>("marketing");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setError("");
    setDownloading(true);
    try {
      const res = await apiClient.getExport(id, mode);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      setError(err.message || "Export not available yet");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-8">
        <Link
          href={`/listings/${id}`}
          className="text-sm text-[var(--color-primary)] hover:underline mb-4 inline-block"
        >
          &larr; Back to Listing
        </Link>

        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-6"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Export Package
        </h1>

        {/* Toggle */}
        <div className="flex rounded-xl bg-white/50 backdrop-blur border border-white/30 p-1 mb-6">
          {(["mls", "marketing"] as const).map((m) => (
            <motion.button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                mode === m
                  ? "bg-[var(--color-primary)] text-white shadow-md"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
              whileTap={{ scale: 0.98 }}
            >
              {m === "mls" ? "MLS" : "Marketing"}
            </motion.button>
          ))}
        </div>

        {/* Bundle contents */}
        <GlassCard tilt={false} className="mb-6">
          <h3
            className="text-lg font-semibold mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            {MODE_INFO[mode].title}
          </h3>
          <ul className="space-y-2">
            {MODE_INFO[mode].items.map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-[var(--color-text)]">
                <span className="text-green-500">&#10003;</span>
                {item}
              </li>
            ))}
          </ul>
        </GlassCard>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        <Button onClick={handleDownload} loading={downloading} className="w-full">
          Download {mode === "mls" ? "MLS" : "Marketing"} Package
        </Button>
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
