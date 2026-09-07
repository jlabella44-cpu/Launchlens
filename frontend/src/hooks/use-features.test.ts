import { describe, expect, it } from "vitest";
import { parseFeatures } from "./use-features";

describe("parseFeatures", () => {
  it("returns a set of enabled names", () => {
    expect(parseFeatures({ features: ["microsite", "webhooks"] }).has("microsite")).toBe(true);
    expect(parseFeatures({ features: ["microsite"] }).has("learning")).toBe(false);
  });
  it("tolerates a missing body", () => {
    expect(parseFeatures(undefined).size).toBe(0);
  });
});
