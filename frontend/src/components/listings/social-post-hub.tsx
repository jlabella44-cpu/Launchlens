"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
import type { ScheduledPost } from "@/lib/types";
import { PlatformPostCard } from "./platform-post-card";
import type { CaptionStyle } from "./caption-hook-selector";

interface ListingEvent {
  id: string;
  event_type: string;
  event_data: Record<string, any>;
  created_at: string;
}

interface SocialAccount {
  id: string;
  platform: string;
  platform_username: string;
  status: string;
}

interface SocialCutInfo {
  platform: string;
  download_url: string;
  preview_url?: string;
}

interface SocialContent {
  captions?: Partial<Record<CaptionStyle, string>>;
  instagram_captions?: Partial<Record<CaptionStyle, string>>;
  facebook_captions?: Partial<Record<CaptionStyle, string>>;
  hashtags?: string[];
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    published: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400",
    scheduled: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
    publishing: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400",
    failed: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400",
    cancelled: "bg-slate-100 text-slate-500",
    draft: "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${styles[status] || styles.draft}`}>
      {status}
    </span>
  );
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  just_listed: "Just Listed",
  open_house: "Open House",
  price_drop: "Price Reduction",
  under_contract: "Under Contract",
  sold: "Sold",
};

interface SocialPostHubProps {
  listingId: string;
}

export function SocialPostHub({ listingId }: SocialPostHubProps) {
  const [events, setEvents] = useState<ListingEvent[]>([]);
  const [socialContent, setSocialContent] = useState<SocialContent | null>(null);
  const [socialCuts, setSocialCuts] = useState<SocialCutInfo[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeEvent, setActiveEvent] = useState<ListingEvent | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [evts, accounts] = await Promise.all([
          apiClient.getListingEvents(listingId),
          apiClient.getSocialAccounts(),
        ]);
        setEvents(evts);
        setSocialAccounts(accounts);
        if (evts.length > 0) setActiveEvent(evts[0]);

        // Social content — try, fall back gracefully
        try {
          const content = await apiClient.getSocialContent(listingId);
          setSocialContent(content);
        } catch {
          setSocialContent(null);
        }

        // Social cuts
        try {
          const cuts = await apiClient.getSocialCuts(listingId);
          setSocialCuts(cuts as any);
        } catch {
          setSocialCuts([]);
        }

        // Scheduled/published posts
        try {
          const posts = await apiClient.listSocialPosts(listingId);
          setScheduledPosts(posts);
        } catch {
          setScheduledPosts([]);
        }
      } catch {
        // non-fatal
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [listingId]);

  function getCutForPlatform(platform: string): SocialCutInfo | undefined {
    return socialCuts.find(
      (c) => c.platform?.toLowerCase() === platform.toLowerCase()
    );
  }

  function getAccountUsername(platform: string): string | undefined {
    return socialAccounts.find(
      (a) => a.platform?.toLowerCase() === platform.toLowerCase()
    )?.platform_username;
  }

  function getCaptions(platform: string): Partial<Record<CaptionStyle, string>> {
    if (!socialContent) return {};
    // Platform-specific captions > shared captions
    if (platform === "instagram" && socialContent.instagram_captions) {
      return socialContent.instagram_captions;
    }
    if (platform === "facebook" && socialContent.facebook_captions) {
      return socialContent.facebook_captions;
    }
    // TikTok reuses Instagram captions
    if (platform === "tiktok") {
      return socialContent.instagram_captions ?? socialContent.captions ?? {};
    }
    return socialContent.captions ?? {};
  }

  async function handleMarkPosted(platform: string) {
    if (!activeEvent) return;
    try {
      await apiClient.markEventPosted(listingId, activeEvent.id, platform);
    } catch {
      // silent
    }
  }

  function isAccountConnected(platform: string): boolean {
    return socialAccounts.some(
      (a) => a.platform?.toLowerCase() === platform.toLowerCase() && a.status === "connected"
    );
  }

  async function handlePublishNow(platform: string, caption: string, hashtags: string[]) {
    try {
      const cut = getCutForPlatform(platform);
      const mediaKeys = cut ? [cut.download_url] : [];
      const post = await apiClient.publishNow(listingId, { platform, caption, hashtags, media_s3_keys: mediaKeys });
      setScheduledPosts((prev) => [post, ...prev]);
      if (activeEvent) {
        await apiClient.markEventPosted(listingId, activeEvent.id, platform);
      }
    } catch {
      // error handled by caller via toast
    }
  }

  async function handleCancelPost(postId: string) {
    try {
      const updated = await apiClient.cancelSocialPost(postId);
      setScheduledPosts((prev) => prev.map((p) => (p.id === postId ? updated : p)));
    } catch {
      // silent
    }
  }

  async function handleRetryPost(postId: string) {
    try {
      const updated = await apiClient.retrySocialPost(postId);
      setScheduledPosts((prev) => prev.map((p) => (p.id === postId ? updated : p)));
    } catch {
      // silent
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Event context banner */}
      {events.length > 0 ? (
        <div className="bg-white dark:bg-[rgba(15,27,45,0.8)] rounded-2xl border border-slate-100 dark:border-white/10 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
            Posting Context
          </p>
          <div className="flex flex-wrap gap-2">
            {events.map((evt) => (
              <button
                key={evt.id}
                onClick={() => setActiveEvent(evt)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors focus:outline-none ${
                  activeEvent?.id === evt.id
                    ? "bg-[#F97316] text-white"
                    : "bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/20"
                }`}
              >
                {EVENT_TYPE_LABELS[evt.event_type] ?? evt.event_type}
              </button>
            ))}
          </div>
          {activeEvent && (
            <p className="text-xs text-slate-400 mt-2">
              {EVENT_TYPE_LABELS[activeEvent.event_type] ?? activeEvent.event_type} &middot;{" "}
              {new Date(activeEvent.created_at).toLocaleDateString()}
            </p>
          )}
        </div>
      ) : (
        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/30 rounded-2xl p-5 text-center">
          <p className="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-1">
            No listing events yet
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Events like "Just Listed" or "Open House" will appear here once created.
          </p>
        </div>
      )}

      {/* Platform cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(["instagram", "facebook", "tiktok"] as const).map((platform) => (
          <PlatformPostCard
            key={platform}
            platform={platform}
            listingId={listingId}
            eventId={activeEvent?.id}
            socialCut={getCutForPlatform(platform)}
            captions={getCaptions(platform)}
            hashtags={socialContent?.hashtags}
            connectedUsername={getAccountUsername(platform)}
            isOAuthConnected={isAccountConnected(platform)}
            onMarkPosted={handleMarkPosted}
            onPublishNow={handlePublishNow}
          />
        ))}
      </div>

      {/* Post Status Section */}
      {scheduledPosts.length > 0 && (
        <div className="bg-white dark:bg-[rgba(15,27,45,0.8)] rounded-2xl border border-slate-100 dark:border-white/10 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-3">
            Publishing Activity
          </p>
          <div className="space-y-2">
            {scheduledPosts.map((post) => (
              <div key={post.id} className="flex items-center gap-3 p-2 rounded-lg bg-slate-50 dark:bg-white/5">
                <span className="text-xs font-semibold capitalize w-20">{post.platform}</span>
                <StatusBadge status={post.status} />
                <span className="flex-1 text-xs text-slate-500 truncate">{post.caption.slice(0, 60)}...</span>
                {post.platform_post_url && (
                  <a href={post.platform_post_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--color-primary)] hover:underline">
                    View
                  </a>
                )}
                {post.status === "scheduled" && (
                  <button onClick={() => handleCancelPost(post.id)} className="text-xs text-red-500 hover:underline">Cancel</button>
                )}
                {post.status === "failed" && (
                  <button onClick={() => handleRetryPost(post.id)} className="text-xs text-[#F97316] hover:underline">Retry</button>
                )}
                {post.error_message && post.status === "failed" && (
                  <span className="text-[10px] text-red-400" title={post.error_message}>Error</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
