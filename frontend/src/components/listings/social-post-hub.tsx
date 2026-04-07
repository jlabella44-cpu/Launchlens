"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
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
            onMarkPosted={handleMarkPosted}
          />
        ))}
      </div>
    </div>
  );
}
