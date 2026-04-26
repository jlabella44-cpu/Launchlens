import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import PerformanceIntelligencePage from "./page";
import apiClient from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  default: {
    getPerformanceOverview: vi.fn(),
  },
}));

describe("PerformanceIntelligencePage", () => {
  beforeEach(() => {
    vi.mocked(apiClient.getPerformanceOverview).mockReset();
  });

  it("loads performance data through the authenticated api client", async () => {
    vi.mocked(apiClient.getPerformanceOverview).mockResolvedValue({
      tenant_id: "tenant-1",
      total_outcomes: 0,
      insights: [],
      sufficient_data: false,
    });

    render(<PerformanceIntelligencePage />);

    await waitFor(() => {
      expect(apiClient.getPerformanceOverview).toHaveBeenCalledTimes(1);
    });
  });
});