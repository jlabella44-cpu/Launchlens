"use client";

import { useState, useCallback } from "react";
import { CaptionHookSelector, type CaptionStyle } from "./caption-hook-selector";
import { useToast } from "@/components/ui/toast";

interface SocialCutInfo {
  platform: string;
  download_url: string;
  preview_url?: string;
}

interface PlatformPostCardProps {
  platform: "instagram" | "facebook" | "tiktok";
  listingId: string;
  eventId?: string;
  socialCut?: SocialCutInfo;
  captions: Partial<Record<CaptionStyle, string>>;
  hashtags?: string[];
  connectedUsername?: string;
  isOAuthConnected?: boolean;
  isPosted?: boolean;
  onMarkPosted?: (platform: string) => void;
  onPublishNow?: (platform: string, caption: string, hashtags: string[]) => Promise<void>;
}

const PLATFORM_CONFIG = {
  instagram: {
    label: "Instagram",
    color: "from-purple-500 to-pink-500",
    showHashtags: true,
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    ),
  },
  facebook: {
    label: "Facebook",
    color: "from-blue-600 to-blue-500",
    showHashtags: false,
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
  },
  tiktok: {
    label: "TikTok",
    color: "from-slate-900 to-slate-700",
    showHashtags: true,
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V9.15a8.15 8.15 0 004.78 1.52V7.22a4.85 4.85 0 01-1.01-.53z" />
      </svg>
    ),
  },
};

export function PlatformPostCard({
  platform,
  listingId,
  eventId,
  socialCut,
  captions,
  hashtags = [],
  connectedUsername,
  isOAuthConnected = false,
  isPosted = false,
  onMarkPosted,
  onPublishNow,
}: PlatformPostCardProps) {
  const config = PLATFORM_CONFIG[platform];
  const { toast } = useToast();
  const [currentCaption, setCurrentCaption] = useState("");
  const [marked, setMarked] = useState(isPosted);
  const [publishing, setPublishing] = useState(false);

  const handleCaptionSelect = useCallback((_style: CaptionStyle, text: string) => {
    setCurrentCaption(text);
  }, []);

  function buildClipboardText() {
    const parts = [currentCaption];
    if (config.showHashtags && hashtags.length > 0) {
      parts.push("\n\n" + hashtags.map((h) => `#${h}`).join(" "));
    }
    return parts.join("");
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(buildClipboardText());
      toast("Caption copied to clipboard", "success");
    } catch {
      toast("Could not copy — please copy manually", "error");
    }
  }

  function handleDownload() {
    if (!socialCut?.download_url) return;
    const a = document.createElement("a");
    a.href = socialCut.download_url;
    a.download = `${platform}-cut.mp4`;
    a.click();
  }

  function handleMarkPosted(checked: boolean) {
    setMarked(checked);
    if (checked && onMarkPosted) onMarkPosted(platform);
  }

  return (
    <div className="bg-white dark:bg-[rgba(15,27,45,0.8)] rounded-2xl border border-slate-100 dark:border-white/10 overflow-hidden flex flex-col">
      {/* Platform header */}
      <div className={`bg-gradient-to-r ${config.color} px-4 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-2 text-white">
          {config.icon}
          <span className="font-semibold text-sm">{config.label}</span>
        </div>
        {connectedUsername && (
          <span className="text-xs bg-white/20 text-white px-2 py-0.5 rounded-full font-medium">
            @{connectedUsername}
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-3 flex-1">
        {/* Video preview */}
        {socialCut?.preview_url ? (
          <video
            src={socialCut.preview_url}
            controls
            playsInline
            className="w-full aspect-[9/16] rounded-xl object-cover bg-slate-100"
          />
        ) : socialCut?.download_url ? (
          <video
            src={socialCut.download_url}
            controls
            playsInline
            className="w-full aspect-[9/16] rounded-xl object-cover bg-slate-100"
          />
        ) : (
          <div className="w-full aspect-[9/16] rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
            <p className="text-xs text-slate-400">No video cut available</p>
          </div>
        )}

        {/* Caption selector */}
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1.5">
            Caption Hook
          </p>
          <CaptionHookSelector
            captions={captions}
            platform={platform}
            listingId={listingId}
            onSelect={handleCaptionSelect}
          />
        </div>

        {/* Hashtags (IG + TikTok only) */}
        {config.showHashtags && hashtags.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
              Hashtags
            </p>
            <p className="text-xs text-[var(--color-primary)] leading-relaxed">
              {hashtags.map((h) => `#${h}`).join(" ")}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-auto">
          {/* Publish Now — only for OAuth-connected accounts */}
          {isOAuthConnected && onPublishNow && (
            <button
              onClick={async () => {
                setPublishing(true);
                try {
                  await onPublishNow(platform, currentCaption, hashtags);
                  toast(`Published to ${config.label}!`, "success");
                  setMarked(true);
                } catch (err: unknown) {
                  toast(err instanceof Error ? err.message : "Publish failed", "error");
                } finally {
                  setPublishing(false);
                }
              }}
              disabled={publishing || !currentCaption}
              className="flex-1 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
            >
              {publishing ? (
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
              Publish
            </button>
          )}
          <button
            onClick={handleCopy}
            className="flex-1 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-xs font-semibold text-[var(--color-text-secondary)] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors inline-flex items-center justify-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy
          </button>
          {socialCut?.download_url && (
            <button
              onClick={handleDownload}
              className="flex-1 py-2 rounded-lg bg-[#F97316] hover:bg-[#ea580c] text-white text-xs font-semibold transition-colors inline-flex items-center justify-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </button>
          )}
        </div>

        {/* Mark as posted */}
        <label className="flex items-center gap-2 cursor-pointer select-none mt-1">
          <input
            type="checkbox"
            checked={marked}
            onChange={(e) => handleMarkPosted(e.target.checked)}
            className="w-4 h-4 rounded accent-[#F97316] cursor-pointer"
          />
          <span className={`text-xs font-medium ${marked ? "text-green-600" : "text-slate-400"}`}>
            {marked ? "Posted" : "Mark as posted"}
          </span>
        </label>
      </div>
    </div>
  );
}
