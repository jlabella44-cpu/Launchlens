import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act, cleanup } from "@testing-library/react";
import type { ListingEvent } from "@/lib/use-listing-events";

// --- module doubles ------------------------------------------------------

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "listing-1" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/listings/listing-1",
}));

vi.mock("@/lib/api-client", () => {
  const client = {
    getListing: vi.fn(),
    getAssets: vi.fn(),
    getPackage: vi.fn(),
    getMicrosite: vi.fn(),
    getPipelineStatus: vi.fn(),
  };
  return { default: client, apiClient: client };
});

let hookState: {
  connected: boolean;
  lastEvent: ListingEvent | null;
  events: ListingEvent[];
  gaveUp: boolean;
  reset: () => void;
};

vi.mock("@/lib/use-listing-events", () => ({
  useListingEvents: () => hookState,
}));

vi.mock("@/components/layout/nav", () => ({ Nav: () => null }));
vi.mock("@/components/layout/protected-route", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/hooks/use-features", () => ({ useFeature: () => false }));
vi.mock("@/components/ui/toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock("@/components/listings/pipeline-progress", () => ({
  PipelineProgress: () => null,
}));
vi.mock("@/components/listings/package-viewer", () => ({ PackageViewer: () => null }));
vi.mock("@/components/listings/asset-upload-form", () => ({ AssetUploadForm: () => null }));
vi.mock("@/components/listings/video-player", () => ({ VideoPlayer: () => null }));
vi.mock("@/components/listings/social-preview", () => ({ SocialPreview: () => null }));
vi.mock("@/components/listings/share-panel", () => ({ SharePanel: () => null }));
vi.mock("@/components/listings/activity-log", () => ({ ActivityLog: () => null }));
vi.mock("@/components/listings/health-panel", () => ({ HealthPanel: () => null }));
vi.mock("@/components/listings/dollhouse-card", () => ({ DollhouseCard: () => null }));

import ListingDetailPage from "@/app/listings/[id]/page";
import apiClient from "@/lib/api-client";

const getListing = vi.mocked(apiClient.getListing);
const getAssets = vi.mocked(apiClient.getAssets);

function event(type: string): ListingEvent {
  return { event_type: type, payload: {}, timestamp: null };
}

const LISTING = {
  id: "listing-1",
  state: "analyzing",
  address: { street: "1 SSE Lane", city: "Austin", state: "TX", zip: "78701" },
  metadata: {},
  created_at: "2026-09-07T00:00:00Z",
} as unknown as Awaited<ReturnType<typeof apiClient.getListing>>;

describe("listing page SSE refetch debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getListing.mockReset().mockResolvedValue(LISTING);
    getAssets.mockReset().mockResolvedValue([]);
    hookState = {
      connected: true,
      lastEvent: null,
      events: [],
      gaveUp: false,
      reset: vi.fn(),
    };
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  /** Let queued promise callbacks run while timers are faked. */
  async function flush() {
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  it("collapses a burst of events into a single refetch", async () => {
    const view = render(<ListingDetailPage />);
    await flush();

    // The initial mount load.
    expect(getListing).toHaveBeenCalledTimes(1);

    // Three events inside 100 ms.
    for (const type of ["ingestion.completed", "coverage.completed", "packaging.completed"]) {
      hookState = { ...hookState, lastEvent: event(type), events: [...hookState.events, event(type)] };
      view.rerender(<ListingDetailPage />);
      await act(async () => {
        vi.advanceTimersByTime(50);
      });
    }

    // Debounce has not fired yet (last event was 0 ms ago).
    expect(getListing).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    await flush();

    expect(getListing).toHaveBeenCalledTimes(2);
  });

  it("shows the live-updates note once the hook gives up", async () => {
    hookState = { ...hookState, connected: false, gaveUp: true };
    const { getByTestId } = render(<ListingDetailPage />);
    await flush();

    expect(getByTestId("live-updates-unavailable")).toBeInTheDocument();
  });
});
