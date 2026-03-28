"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DemoPipelineStatus } from "@/components/listings/demo-pipeline-status";
import apiClient from "@/lib/api-client";
import type { DemoViewResponse } from "@/lib/types";

export default function DemoResultsPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [demo, setDemo] = useState<DemoViewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);

  useEffect(() => {
    apiClient
      .demoView(id)
      .then(setDemo)
      .catch(() => setDemo(null))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleClaim() {
    setClaiming(true);
    try {
      await apiClient.demoClaim(id);
      router.push("/register?claim=" + id);
    } catch {
      router.push("/register?claim=" + id);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!demo) {
    return (
      <>
        <Nav />
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-[var(--color-text-secondary)]">Demo not found or expired.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <div className="mb-6 text-center">
          <h1
            className="text-3xl font-bold text-[var(--color-text)] mb-2"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Your AI-Curated Package
          </h1>
          <Badge state={demo.state} />
        </div>

        <div className="mb-6">
          <DemoPipelineStatus state={demo.state} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 mb-8">
          {(demo.photos ?? []).map((photo, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
            >
              <GlassCard tilt className="p-3">
                <div className="aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 rounded-lg mb-2 flex items-center justify-center">
                  <span className="text-xs text-slate-400 font-mono truncate px-2">
                    {photo.file_path.split("/").pop()}
                  </span>
                </div>
                {photo.room_label && (
                  <p className="text-xs font-medium text-[var(--color-text)] capitalize">
                    {photo.room_label.replace(/_/g, " ")}
                  </p>
                )}
                {photo.quality_score != null && (
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Score: {photo.quality_score}
                  </p>
                )}
              </GlassCard>
            </motion.div>
          ))}
        </div>

        <div className="text-center">
          <GlassCard tilt={false} className="inline-block max-w-md">
            <h3
              className="text-lg font-semibold mb-2"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Ready to launch this listing?
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              Create an account to claim these results, get branded content,
              social posts, MLS bundles, and AI video tours.
            </p>
            <Button onClick={handleClaim} loading={claiming}>
              Claim &amp; Register
            </Button>
          </GlassCard>
        </div>
      </main>
    </>
  );
}
