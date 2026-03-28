"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface ListingEvent {
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: string | null;
}

interface UseListingEventsOptions {
  /** Auto-reconnect on connection loss. Default: true */
  reconnect?: boolean;
  /** Base API URL. Default: http://localhost:8000 */
  baseUrl?: string;
}

/**
 * React hook for consuming real-time pipeline events via SSE.
 *
 * Usage:
 *   const { events, connected, lastEvent } = useListingEvents(listingId);
 */
export function useListingEvents(
  listingId: string | null,
  options: UseListingEventsOptions = {},
) {
  const { reconnect = true, baseUrl = "http://localhost:8000" } = options;

  const [events, setEvents] = useState<ListingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ListingEvent | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const cleanup = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!listingId) {
      cleanup();
      return;
    }

    const token = typeof window !== "undefined"
      ? localStorage.getItem("token")
      : null;

    const url = `${baseUrl}/listings/${listingId}/events${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);

    source.onmessage = (e) => {
      try {
        const event: ListingEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);
        setLastEvent(event);
      } catch {
        // skip malformed events
      }
    };

    // Listen for named pipeline events
    const pipelineEvents = [
      "ingestion.completed", "vision_tier1.completed", "vision_tier2.completed",
      "coverage.completed", "packaging.completed", "content.completed",
      "brand.completed", "social_content.completed", "mls_export.completed",
      "pipeline.completed", "video.completed",
    ];

    for (const eventType of pipelineEvents) {
      source.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const event: ListingEvent = JSON.parse(e.data);
          setEvents((prev) => [...prev, event]);
          setLastEvent(event);
        } catch {
          // skip
        }
      });
    }

    source.onerror = () => {
      setConnected(false);
      if (!reconnect) {
        source.close();
      }
      // EventSource auto-reconnects by default if reconnect=true
    };

    return cleanup;
  }, [listingId, baseUrl, reconnect, cleanup]);

  const reset = useCallback(() => {
    setEvents([]);
    setLastEvent(null);
  }, []);

  return { events, connected, lastEvent, reset };
}
