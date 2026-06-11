import { describe, expect, it } from "vitest";
import { experimentMatchesSearch } from "./experiment-matches-search";

const base = {
  id: "11111111-2222-3333-4444-555555555555",
  name: "alpha-run",
  description: "uses adam optimizer",
  tags: ["baseline", "gpu-a100"],
};

describe("experimentMatchesSearch", () => {
  it("matches empty query", () => {
    expect(experimentMatchesSearch(base, "")).toBe(true);
    expect(experimentMatchesSearch(base, "   ")).toBe(true);
  });

  it("matches name, description, id, and tags", () => {
    expect(experimentMatchesSearch(base, "Alpha")).toBe(true);
    expect(experimentMatchesSearch(base, "ADAM")).toBe(true);
    expect(experimentMatchesSearch(base, "11111111")).toBe(true);
    expect(experimentMatchesSearch(base, "gpu-a100")).toBe(true);
    expect(experimentMatchesSearch(base, "baseline")).toBe(true);
  });

  it("returns false when nothing matches", () => {
    expect(experimentMatchesSearch(base, "sgd-only")).toBe(false);
    expect(experimentMatchesSearch({ ...base, tags: null }, "gpu")).toBe(false);
  });
});
