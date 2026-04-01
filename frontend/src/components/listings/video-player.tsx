"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import apiClient from "@/lib/api-client";
import type { VideoResponse, Chapter } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  ai_generated: "AI Generated",
  professional: "Professional",
  user_raw: "User Upload",
};

interface VideoPlayerProps {
  listingId: string;
  onNoVideo?: () => void;
}

export function VideoPlayer({ listingId, onNoVideo }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [video, setVideo] = useState<VideoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getVideo(listingId)
      .then(setVideo)
      .catch(() => {
        setVideo(null);
        onNoVideo?.();
      })
      .finally(() => setLoading(false));
  }, [listingId, onNoVideo]);

  function seekTo(time: number) {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  }

  if (loading) {
    return (
      <GlassCard tilt={false}>
        <div className="h-48 rounded-lg bg-slate-100 animate-pulse flex items-center justify-center">
          <span className="text-xs text-slate-400">Loading video...</span>
        </div>
      </GlassCard>
    );
  }
  if (!video) return null;

  return (
    <GlassCard tilt={false}>
      <div className="flex items-center justify-between mb-3">
        <h3
          className="text-lg font-semibold"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Property Video
        </h3>
        <span className="text-xs font-medium px-2 py-1 rounded-full bg-blue-100 text-blue-700">
          {TYPE_LABELS[video.video_type] || video.video_type}
        </span>
      </div>

      <video
        ref={videoRef}
        src={`${process.env.NEXT_PUBLIC_API_URL || "/api"}/listings/${listingId}/video/stream?key=${encodeURIComponent(video.s3_key)}`}
        controls
        poster={video.thumbnail_s3_key ? `${process.env.NEXT_PUBLIC_API_URL || "/api"}/listings/${listingId}/video/stream?key=${encodeURIComponent(video.thumbnail_s3_key)}` : undefined}
        className="w-full rounded-lg bg-black"
      />

      {video.duration_seconds && (
        <p className="text-xs text-[var(--color-text-secondary)] mt-2">
          {video.duration_seconds}s
          {video.clip_count && ` · ${video.clip_count} clips`}
        </p>
      )}

      {video.chapters && video.chapters.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-[var(--color-text)] mb-2">Chapters</p>
          <div className="flex flex-wrap gap-1.5">
            {video.chapters.map((ch: Chapter, i: number) => (
              <motion.button
                key={i}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => seekTo(ch.time)}
                className="text-xs px-2.5 py-1 rounded-full bg-white/60 border border-white/30 hover:bg-white/80 transition-colors cursor-pointer"
                title={ch.description}
              >
                <span className="text-[var(--color-text-secondary)]">
                  {Math.floor(ch.time / 60)}:{String(ch.time % 60).padStart(2, "0")}
                </span>{" "}
                <span className="capitalize">{ch.label.replace(/_/g, " ")}</span>
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  );
}
