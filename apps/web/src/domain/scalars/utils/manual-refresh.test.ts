import { describe, expect, it } from "vitest";
import { planManualRefreshActions } from "./manual-refresh";

describe("planManualRefreshActions", () => {
  it("does not full-refetch when incremental refresh succeeds or is unchanged", () => {
    expect(planManualRefreshActions("updated", "unchanged")).toEqual({
      refetchScalars: false,
      refetchArtifacts: false,
    });
    expect(planManualRefreshActions("unchanged", "updated")).toEqual({
      refetchScalars: false,
      refetchArtifacts: false,
    });
  });

  it("falls back to full refetch only for unavailable results", () => {
    expect(planManualRefreshActions("unavailable", "updated")).toEqual({
      refetchScalars: true,
      refetchArtifacts: false,
    });
    expect(planManualRefreshActions("updated", "unavailable")).toEqual({
      refetchScalars: false,
      refetchArtifacts: true,
    });
    expect(planManualRefreshActions("unavailable", "unavailable")).toEqual({
      refetchScalars: true,
      refetchArtifacts: true,
    });
  });
});
