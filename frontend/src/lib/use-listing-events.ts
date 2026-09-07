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
  /** Base API URL. Default: NEXT_PUBLIC_API_URL, else "/api". */
  baseUrl?: string;
}

/**
 * Event names the SSE endpoint forwards. Mirrors `_PIPELINE_EVENTS` in
 * `src/listingjet/api/sse.py`; the backend also forwards any `*.failed`
 * event, so each step name is subscribed in both flavours.
 */
const PIPELINE_STEP_EVENTS = [
  "ingestion", "photo_analysis", "photo_compliance", "coverage", "packaging",
  "content_social", "brand", "mls_export", "video_baseline", "video_ai",
  "social_cuts", "pipeline",
] as const;

export const PIPELINE_EVENT_TYPES: string[] = PIPELINE_STEP_EVENTS.flatMap(
  (name) => [`${name}.completed`, `${name}.failed`],
);

/**
 * Consecutive `onerror` callbacks (with no `onopen` in between) after which
 * we stop letting EventSource retry. Without this the browser reconnects
 * forever against an endpoint that is down, and every attempt costs a
 * request.
 */
const MAX_CONSECUTIVE_ERRORS = 5;

/**
 * React hook for consuming real-time pipeline events via SSE.
 *
 * Usage:
 *   const { events, connected, lastEvent, gaveUp } = useListingEvents(listingId);
 */
export function useListingEvents(
  listingId: string | null,
  options: UseListingEventsOptions = {},
) {
  const { reconnect = true, baseUrl = process.env.NEXT_PUBLIC_API_URL || "/api" } = options;

  const [events, setEvents] = useState<ListingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ListingEvent | null>(null);
  const [gaveUp, setGaveUp] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  /** Event ids already applied — the server replays on reconnect. */
  const seenRef = useRef<Set<string>>(new Set());
  const errorCountRef = useRef(0);

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

    seenRef.current = new Set();
    errorCountRef.current = 0;
    setGaveUp(false);

    // Key must match `auth-context.tsx`'s storage key, or this always
    // reads null and the stream silently falls back to unauthenticated
    // (401) connection attempts.
    const token = typeof window !== "undefined"
      ? localStorage.getItem("listingjet_token")
      : null;

    // NOTE: the SSE router (`api/sse.py`) is mounted at `/sse` in
    // `main.py` to avoid colliding with the pre-existing
    // `GET /listings/{id}/events` route in `api/listing_events.py`
    // (unrelated: social-reminder events, not the pipeline stream).
    const url = `${baseUrl}/sse/listings/${listingId}/events${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    const source = new EventSource(url);
    sourceRef.current = source;

    /**
     * Apply one event, ignoring anything already seen. The SSE `id:` is the
     * identity when present (it survives a reconnect replay); otherwise fall
     * back to type + timestamp.
     */
    const record = (e: MessageEvent) => {
      try {
        const event: ListingEvent = JSON.parse(e.data);
        const key = e.lastEventId || `${event.event_type}|${event.timestamp}`;
        if (seenRef.current.has(key)) return;
        seenRef.current.add(key);
        setEvents((prev) => [...prev, event]);
        setLastEvent(event);
      } catch {
        // skip malformed events
      }
    };

    source.onopen = () => {
      errorCountRef.current = 0;
      setConnected(true);
    };

    source.onmessage = record;

    for (const eventType of PIPELINE_EVENT_TYPES) {
      source.addEventListener(eventType, record as EventListener);
    }

    source.onerror = () => {
      setConnected(false);
      errorCountRef.current += 1;
      if (errorCountRef.current >= MAX_CONSECUTIVE_ERRORS) {
        source.close();
        setGaveUp(true);
        return;
      }
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
    seenRef.current = new Set();
  }, []);

  return { events, connected, lastEvent, gaveUp, reset };
}
