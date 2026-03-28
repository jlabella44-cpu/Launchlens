"use client";

import { useState } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

interface VideoUploadProps {
  listingId: string;
  onUploaded: () => void;
}

export function VideoUpload({ listingId, onUploaded }: VideoUploadProps) {
  const [s3Key, setS3Key] = useState(`videos/${listingId}/`);
  const [videoType, setVideoType] = useState<"professional" | "user_raw">("professional");
  const [duration, setDuration] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!s3Key.startsWith(`videos/${listingId}/`)) {
      setError(`S3 key must start with videos/${listingId}/`);
      return;
    }

    setLoading(true);
    try {
      await apiClient.uploadVideo(listingId, {
        s3_key: s3Key,
        video_type: videoType,
        duration_seconds: duration ? parseInt(duration, 10) : undefined,
      });
      onUploaded();
    } catch (err: any) {
      setError(err.message || "Upload failed");
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
        Add Video
      </h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            S3 Key
          </label>
          <input
            type="text"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
            className="w-full rounded-lg border border-white/30 bg-white/50 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            Video Type
          </label>
          <div className="flex gap-4">
            {(["professional", "user_raw"] as const).map((t) => (
              <label key={t} className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="videoType"
                  checked={videoType === t}
                  onChange={() => setVideoType(t)}
                  className="accent-[var(--color-primary)]"
                />
                <span className="capitalize">{t.replace(/_/g, " ")}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-[var(--color-text)] mb-1">
            Duration (seconds, optional)
          </label>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="60"
            className="w-32 rounded-lg border border-white/30 bg-white/50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex justify-end">
          <Button type="submit" loading={loading}>
            Register Video
          </Button>
        </div>
      </form>
    </GlassCard>
  );
}
