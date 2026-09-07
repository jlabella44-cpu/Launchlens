import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  PipelineStatus,
  STAGES,
  ERROR_STATES,
  getStageIndex,
} from "@/components/listings/pipeline-status";

/**
 * Copied verbatim from `ListingState` in src/listingjet/models/listing.py.
 * If a state is added there and not handled here, this test fails — which is
 * the point: an unmapped state made getStageIndex return -1 and the tracker
 * rendered with no stage marked and no error styling.
 */
const LISTING_STATES = [
  "draft",
  "new",
  "uploading",
  "analyzing",
  "awaiting_review",
  "in_review",
  "approved",
  "delivered",
  "pipeline_timeout",
  "failed",
  "cancelled",
  "exporting",
  "demo",
];

describe("PipelineStatus stage mapping", () => {
  it.each(LISTING_STATES)("maps %s to a stage or the error set", (state) => {
    const index = getStageIndex(state);
    expect(index >= 0 || ERROR_STATES.has(state)).toBe(true);
  });

  it("puts the pre-pipeline states in the first stage", () => {
    expect(getStageIndex("draft")).toBe(0);
    expect(getStageIndex("demo")).toBe(0);
    expect(STAGES[0].key).toBe("ingest");
  });

  it("never claims a stage for an unknown state", () => {
    expect(getStageIndex("not-a-state")).toBe(-1);
  });

  it.each(LISTING_STATES)("renders every stage for %s", (state) => {
    const { unmount } = render(<PipelineStatus state={state} />);
    const markers = screen.getAllByText(/: (active|complete|pending|error)$/);
    expect(markers).toHaveLength(STAGES.length);
    // Non-error states must actually mark their position in the pipeline.
    if (!ERROR_STATES.has(state)) {
      expect(markers.some((m) => !m.textContent?.endsWith("pending"))).toBe(true);
    }
    unmount();
  });
});
