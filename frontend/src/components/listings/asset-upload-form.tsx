"use client";

import { useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

interface AssetUploadFormProps {
  listingId: string;
  onUploaded: () => void;
}

export function AssetUploadForm({ listingId, onUploaded }: AssetUploadFormProps) {
  const [paths, setPaths] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [quotaHit, setQuotaHit] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setQuotaHit(false);
    const lines = paths
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      setError("Enter at least one S3 file path.");
      return;
    }

    setLoading(true);
    try {
      await apiClient.registerAssets(listingId, {
        assets: lines.map((path) => ({
          file_path: path,
          file_hash: path.split("/").pop() || path,
        })),
      });
      setPaths("");
      onUploaded();
    } catch (err: any) {
      if (err.status === 403) {
        setQuotaHit(true);
        setError("You've reached the asset limit for your plan.");
      } else {
        setError(err.message || "Upload failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <GlassCard tilt={false}>
      <h3
        className="text-lg font-semibold mb-3"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Register Assets
      </h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor="paths" className="block text-sm font-medium mb-1">
            S3 file paths (one per line)
          </label>
          <textarea
            id="paths"
            rows={4}
            value={paths}
            onChange={(e) => setPaths(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm font-mono"
            placeholder={"s3://bucket/listing/photo_1.jpg\ns3://bucket/listing/photo_2.jpg"}
          />
        </div>
        {error && (
          <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
            <p>{error}</p>
            {quotaHit && (
              <Link
                href="/pricing"
                className="inline-block mt-2 text-[var(--color-primary)] font-medium hover:underline"
              >
                Upgrade your plan &rarr;
              </Link>
            )}
          </div>
        )}
        <Button type="submit" loading={loading}>
          Register Assets
        </Button>
      </form>
    </GlassCard>
  );
}
