"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

export default function DemoPage() {
  const router = useRouter();
  const [paths, setPaths] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const filePaths = paths
      .split("\n")
      .map((p) => p.trim())
      .filter(Boolean);

    if (filePaths.length < 5) {
      setError("At least 5 photos required");
      return;
    }
    if (filePaths.length > 50) {
      setError("Maximum 50 photos allowed");
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.demoUpload({ file_paths: filePaths });
      router.push(`/demo/${res.demo_id}`);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl w-full text-center"
        >
          <h1
            className="text-4xl font-bold text-[var(--color-text)] mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            See AI Results in Minutes
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-8">
            Paste your listing photo S3 paths below. Our AI will curate, score,
            and package them — no account needed.
          </p>

          <GlassCard tilt={false} className="text-left">
            <form onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-2">
                Photo paths (one per line, 5–50 photos)
              </label>
              <textarea
                value={paths}
                onChange={(e) => setPaths(e.target.value)}
                rows={8}
                placeholder={`listings/demo/exterior.jpg\nlistings/demo/living_room.jpg\nlistings/demo/kitchen.jpg\nlistings/demo/bedroom.jpg\nlistings/demo/bathroom.jpg`}
                className="w-full rounded-lg border border-white/30 bg-white/50 backdrop-blur px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-none"
              />
              {error && (
                <p className="text-red-500 text-sm mt-2">{error}</p>
              )}
              <div className="mt-4 flex justify-end">
                <Button type="submit" loading={loading}>
                  Process Photos
                </Button>
              </div>
            </form>
          </GlassCard>
        </motion.div>
      </main>
    </>
  );
}
