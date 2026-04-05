/**
 * Lightweight analytics tracking for ListingJet launch.
 *
 * Sends events to the backend and optionally to external providers
 * (Meta Pixel, PostHog) when configured via environment variables.
 */

type EventProperties = Record<string, string | number | boolean | null>;

const ANALYTICS_ENDPOINT = `${process.env.NEXT_PUBLIC_API_URL || "/api"}/analytics/events`;

/** Parse UTM parameters from the current URL and cache them for the session. */
function getUtmParams(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const cached = sessionStorage.getItem("lj_utm");
  if (cached) return JSON.parse(cached);

  const params = new URLSearchParams(window.location.search);
  const utm: Record<string, string> = {};
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]) {
    const val = params.get(key);
    if (val) utm[key] = val;
  }
  if (Object.keys(utm).length > 0) {
    sessionStorage.setItem("lj_utm", JSON.stringify(utm));
  }
  return utm;
}

/** Get or create an anonymous session ID for pre-auth attribution. */
function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = sessionStorage.getItem("lj_sid");
  if (!sid) {
    sid = crypto.randomUUID();
    sessionStorage.setItem("lj_sid", sid);
  }
  return sid;
}

/**
 * Track an analytics event. Fire-and-forget — never blocks UI.
 *
 * @param event - Event name (e.g. "signup", "first_upload", "cta_click")
 * @param properties - Arbitrary key/value metadata
 */
export function trackEvent(event: string, properties: EventProperties = {}): void {
  const payload = {
    event,
    properties: {
      ...properties,
      ...getUtmParams(),
      session_id: getSessionId(),
      url: typeof window !== "undefined" ? window.location.pathname : "",
      timestamp: new Date().toISOString(),
    },
  };

  // Send to our backend (best-effort)
  fetch(ANALYTICS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {
    // Silently fail — analytics should never break the app
  });

  // Meta Pixel (if loaded)
  if (typeof window !== "undefined" && (window as any).fbq) {
    (window as any).fbq("trackCustom", event, properties);
  }
}

/** Standard events for consistent naming across the app. */
export const AnalyticsEvents = {
  SIGNUP: "signup",
  FIRST_UPLOAD: "first_upload",
  FIRST_EXPORT: "first_export",
  UPGRADE: "upgrade",
  CTA_CLICK: "cta_click",
  REFERRAL_SENT: "referral_sent",
  REFERRAL_CONVERTED: "referral_converted",
  PAGE_VIEW: "page_view",
} as const;
