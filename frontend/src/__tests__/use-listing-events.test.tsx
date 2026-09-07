import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { useListingEvents } from "@/lib/use-listing-events";

type Handler = (e: MessageEvent) => void;

class StubEventSource {
  static instances: StubEventSource[] = [];

  url: string;
  closed = false;
  onopen: ((e: Event) => void) | null = null;
  onmessage: Handler | null = null;
  onerror: ((e: Event) => void) | null = null;
  private listeners: Record<string, Handler[]> = {};

  constructor(url: string) {
    this.url = url;
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: Handler) {
    (this.listeners[type] ||= []).push(fn);
  }

  removeEventListener(type: string, fn: Handler) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn);
  }

  close() {
    this.closed = true;
  }

  /** Test helper: fire a named SSE event. */
  emit(type: string, data: unknown) {
    for (const fn of this.listeners[type] || []) {
      fn({ data: JSON.stringify(data) } as MessageEvent);
    }
  }

  listenerTypes() {
    return Object.keys(this.listeners);
  }
}

function Probe({ id }: { id: string | null }) {
  const { connected, events, lastEvent } = useListingEvents(id, {
    baseUrl: "http://localhost:8000",
  });
  return (
    <div>
      <span data-testid="connected">{String(connected)}</span>
      <span data-testid="count">{events.length}</span>
      <span data-testid="last">{lastEvent?.event_type ?? "none"}</span>
    </div>
  );
}

describe("useListingEvents", () => {
  beforeEach(() => {
    StubEventSource.instances = [];
    vi.stubGlobal("EventSource", StubEventSource);
    localStorage.setItem("listingjet_token", "tok-123");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  function source() {
    return StubEventSource.instances[0];
  }

  it("opens a stream for the listing with the auth token", () => {
    render(<Probe id="listing-1" />);
    expect(StubEventSource.instances).toHaveLength(1);
    expect(source().url).toBe(
      "http://localhost:8000/sse/listings/listing-1/events?token=tok-123",
    );
  });

  it("flips connected on open", () => {
    render(<Probe id="listing-1" />);
    expect(screen.getByTestId("connected")).toHaveTextContent("false");
    act(() => {
      source().onopen?.(new Event("open"));
    });
    expect(screen.getByTestId("connected")).toHaveTextContent("true");
  });

  it("records a named pipeline event in events and lastEvent", () => {
    render(<Probe id="listing-1" />);
    act(() => {
      source().emit("packaging.completed", {
        event_type: "packaging.completed",
        payload: { listing_id: "listing-1" },
        timestamp: "2026-09-07T00:00:00Z",
      });
    });
    expect(screen.getByTestId("count")).toHaveTextContent("1");
    expect(screen.getByTestId("last")).toHaveTextContent("packaging.completed");
  });

  it("records failure events", () => {
    render(<Probe id="listing-1" />);
    act(() => {
      source().emit("pipeline.failed", {
        event_type: "pipeline.failed",
        payload: { error: "boom" },
        timestamp: null,
      });
    });
    expect(screen.getByTestId("last")).toHaveTextContent("pipeline.failed");

    act(() => {
      source().emit("photo_analysis.failed", {
        event_type: "photo_analysis.failed",
        payload: {},
        timestamp: null,
      });
    });
    expect(screen.getByTestId("last")).toHaveTextContent("photo_analysis.failed");
    expect(screen.getByTestId("count")).toHaveTextContent("2");
  });

  it("subscribes to both completed and failed step events", () => {
    render(<Probe id="listing-1" />);
    const types = source().listenerTypes();
    expect(types).toContain("pipeline.completed");
    expect(types).toContain("pipeline.failed");
    expect(types).toContain("packaging.completed");
    expect(types).toContain("packaging.failed");
    expect(types).toContain("social_cuts.completed");
  });

  it("closes the stream on unmount", () => {
    const { unmount } = render(<Probe id="listing-1" />);
    expect(source().closed).toBe(false);
    unmount();
    expect(source().closed).toBe(true);
  });

  it("opens nothing without a listing id", () => {
    render(<Probe id={null} />);
    expect(StubEventSource.instances).toHaveLength(0);
  });
});
