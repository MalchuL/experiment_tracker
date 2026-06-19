import { describe, expect, it } from "vitest";
import {
  createScalarComparePlotConfig,
  patchScalarComparePlotConfig,
  resolveCommittedMaxPoints,
  resolveCommittedStepBound,
} from "./scalar-compare-plot-config";

describe("resolveCommittedMaxPoints", () => {
  it("keeps draft-only edits separate until commit", () => {
    const plot = createScalarComparePlotConfig(1000);
    const draftOnly = { ...plot, maxPointsDraft: "2500" };

    expect(draftOnly.appliedMaxPoints).toBe(1000);
    expect(draftOnly.maxPointsDraft).toBe("2500");
  });

  it("commits valid positive integers", () => {
    expect(resolveCommittedMaxPoints("2500", 1000)).toEqual({
      appliedMaxPoints: 2500,
      maxPointsDraft: "2500",
      changed: true,
    });
  });

  it("floors fractional values on commit", () => {
    expect(resolveCommittedMaxPoints("12.8", 1000)).toEqual({
      appliedMaxPoints: 12,
      maxPointsDraft: "12",
      changed: true,
    });
  });

  it("does not cap committed values used for live fetches", () => {
    expect(resolveCommittedMaxPoints("2500", 500)).toEqual({
      appliedMaxPoints: 2500,
      maxPointsDraft: "2500",
      changed: true,
    });
  });

  it("reverts invalid values to the applied value", () => {
    expect(resolveCommittedMaxPoints("", 1000)).toEqual({
      appliedMaxPoints: 1000,
      maxPointsDraft: "1000",
      changed: false,
    });
    expect(resolveCommittedMaxPoints("0", 1000)).toEqual({
      appliedMaxPoints: 1000,
      maxPointsDraft: "1000",
      changed: false,
    });
    expect(resolveCommittedMaxPoints("not-a-number", 1000)).toEqual({
      appliedMaxPoints: 1000,
      maxPointsDraft: "1000",
      changed: false,
    });
  });
});

describe("resolveCommittedStepBound", () => {
  it("keeps draft-only step edits separate until commit", () => {
    const plot = createScalarComparePlotConfig(1000);
    const draftOnly = { ...plot, stepMinDraft: "25" };

    expect(draftOnly.stepMin).toBeNull();
    expect(draftOnly.stepMinDraft).toBe("25");
  });

  it("commits valid integer step bounds", () => {
    expect(resolveCommittedStepBound("25", null)).toEqual({
      stepBound: 25,
      stepBoundDraft: "25",
      changed: true,
    });
  });

  it("commits empty step bounds as unset", () => {
    expect(resolveCommittedStepBound("", 25)).toEqual({
      stepBound: null,
      stepBoundDraft: "",
      changed: true,
    });
  });

  it("reverts invalid step bounds to the applied value", () => {
    expect(resolveCommittedStepBound("not-a-number", 25)).toEqual({
      stepBound: 25,
      stepBoundDraft: "25",
      changed: false,
    });
  });
});

describe("patchScalarComparePlotConfig", () => {
  it("updates one plot without changing sibling plot settings", () => {
    const first = { ...createScalarComparePlotConfig(1000), id: "first" };
    const second = { ...createScalarComparePlotConfig(1000), id: "second" };

    const result = patchScalarComparePlotConfig([first, second], "first", {
      metricName: "train/loss",
      maxPointsDraft: "250",
      appliedMaxPoints: 250,
      smoothing: 0.4,
      stepMinDraft: "10",
      stepMin: 10,
      stepMaxDraft: "100",
      stepMax: 100,
    });

    expect(result[0]).toMatchObject({
      id: "first",
      metricName: "train/loss",
      maxPointsDraft: "250",
      appliedMaxPoints: 250,
      smoothing: 0.4,
      stepMinDraft: "10",
      stepMin: 10,
      stepMaxDraft: "100",
      stepMax: 100,
    });
    expect(result[1]).toEqual(second);
    expect(result[1]).not.toBe(result[0]);
  });
});
