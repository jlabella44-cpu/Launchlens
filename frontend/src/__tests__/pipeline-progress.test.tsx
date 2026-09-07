import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { PipelineProgress } from "@/components/listings/pipeline-progress";
import apiClient from "@/lib/api-client";
import type { PipelineStep } from "@/lib/types";

vi.mock("@/lib/api-client", () => {
  const client = { getPipelineStatus: vi.fn() };
  return { default: client, apiClient: client };
});

const getPipelineStatus = vi.mocked(apiClient.getPipelineStatus);

const LONG_ERROR = "Vision provider rejected the request. ".repeat(20);

const STEPS: PipelineStep[] = [
  {
    name: "ingestion",
    status: "completed",
    completed_at: "2026-09-07T10:00:00Z",
    progress: null,
    error: null,
    attempts: 1,
  },
  {
    name: "photo_analysis",
    status: "failed",
    completed_at: null,
    progress: null,
    error: LONG_ERROR,
    attempts: 3,
  },
];

async function renderProgress(props: {
  listingState: string;
  refreshKey?: number;
  live: boolean;
}) {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <PipelineProgress
        listingId="listing-1"
        listingState={props.listingState}
        refreshKey={props.refreshKey ?? 0}
        live={props.live}
      />,
    );
  });
  return result;
}

describe("PipelineProgress", () => {
  let setIntervalSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    getPipelineStatus.mockReset();
    getPipelineStatus.mockResolvedValue({
      listing_id: "listing-1",
      state: "analyzing",
      steps: STEPS,
    });
    setIntervalSpy = vi.spyOn(globalThis, "setInterval");
  });

  afterEach(() => {
    cleanup();
    setIntervalSpy.mockRestore();
    vi.useRealTimers();
  });

  function pollCount() {
    return setIntervalSpy.mock.calls.filter((c: unknown[]) => c[1] === 10_000).length;
  }

  it("schedules no poll while the SSE stream is live", async () => {
    await renderProgress({ listingState: "analyzing", live: true });
    expect(getPipelineStatus).toHaveBeenCalledTimes(1);
    expect(pollCount()).toBe(0);
  });

  it("schedules one poll when not live in a processing state", async () => {
    await renderProgress({ listingState: "analyzing", live: false });
    expect(pollCount()).toBe(1);
  });

  it("schedules no poll in a terminal state even when not live", async () => {
    await renderProgress({ listingState: "delivered", live: false });
    expect(pollCount()).toBe(0);
  });

  it("refetches when refreshKey changes", async () => {
    const { rerender } = await renderProgress({
      listingState: "analyzing",
      live: true,
      refreshKey: 0,
    });
    expect(getPipelineStatus).toHaveBeenCalledTimes(1);
    await act(async () => {
      rerender(
        <PipelineProgress
          listingId="listing-1"
          listingState="analyzing"
          refreshKey={1}
          live
        />,
      );
    });
    expect(getPipelineStatus).toHaveBeenCalledTimes(2);
  });

  it("renders a failed step's error truncated, with the full text in title", async () => {
    await renderProgress({ listingState: "failed", live: true });
    const node = screen.getByTestId("step-error-photo_analysis");
    expect(node.textContent?.length).toBeLessThanOrEqual(201);
    expect(node.textContent).toContain("Vision provider rejected the request.");
    expect(node).toHaveAttribute("title", LONG_ERROR);
  });

  it("shows the attempt count when a step was retried", async () => {
    await renderProgress({ listingState: "failed", live: true });
    expect(screen.getByText(/attempt 3/i)).toBeInTheDocument();
  });

  it("reports steps to the parent via onSteps", async () => {
    const onSteps = vi.fn();
    await act(async () => {
      render(
        <PipelineProgress
          listingId="listing-1"
          listingState="failed"
          refreshKey={0}
          live
          onSteps={onSteps}
        />,
      );
    });
    expect(onSteps).toHaveBeenCalledWith(STEPS);
  });
});
