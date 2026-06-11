import { describe, expect, it } from "vitest";
import type { Experiment } from "@/domain/experiments/types";
import {
  buildScalarsQueryString,
  parseScalarsQueryParams,
  syncSelectedExperimentsOnListGrowth,
  toggleExperimentSelection,
  toggleHiddenArtifact,
  toggleHiddenMetric,
} from "./scalars-query-state";
import { decodeStringSelection } from "./selection-codec";

const experiments = [
  { id: "exp-1", name: "A", createdAt: "2026-05-20T10:00:00.000Z" },
  { id: "exp-2", name: "B", createdAt: "2026-05-19T10:00:00.000Z" },
] as Experiment[];

describe("buildScalarsQueryString", () => {
  it("encodes hidden slash-prefixed metrics and artifacts", () => {
    const query = buildScalarsQueryString(
      new Set(["exp-1"]),
      new Set(["train/loss"]),
      new Set(["image:train/sample"]),
      0.25,
      2
    );

    const params = new URLSearchParams(query);
    expect(decodeStringSelection(params.get("exp"))).toEqual(["exp-1"]);
    expect(decodeStringSelection(params.get("met"))).toEqual(["train/loss"]);
    expect(decodeStringSelection(params.get("art"))).toEqual(["image:train/sample"]);
    expect(params.get("s")).toBe("0.25");
  });
});

describe("parseScalarsQueryParams", () => {
  it("roundtrips slash-prefixed hidden metrics and artifacts", () => {
    const params = new URLSearchParams(
      buildScalarsQueryString(
        new Set(["exp-2"]),
        new Set(["train/loss"]),
        new Set(["image:train/sample"]),
        0,
        2
      )
    );

    const parsed = parseScalarsQueryParams(
      params,
      experiments,
      ["loss", "train/loss"],
      ["image:train/sample", "pie:val/dist"]
    );

    expect(parsed.selectedExperimentIds).toEqual(new Set(["exp-2"]));
    expect(parsed.hiddenMetrics).toEqual(new Set(["train/loss"]));
    expect(parsed.hiddenArtifactIds).toEqual(new Set(["image:train/sample"]));
  });
});

describe("syncSelectedExperimentsOnListGrowth", () => {
  it("expands selection when user previously had every experiment selected", () => {
    const next = syncSelectedExperimentsOnListGrowth({
      selected: new Set(["exp-1", "exp-2"]),
      previousExperimentIds: new Set(["exp-1", "exp-2"]),
      currentExperimentIds: new Set(["exp-1", "exp-2", "exp-3"]),
    });

    expect(next).toEqual(new Set(["exp-1", "exp-2", "exp-3"]));
  });

  it("drops stale ids without expanding partial selections", () => {
    const next = syncSelectedExperimentsOnListGrowth({
      selected: new Set(["exp-1", "exp-missing"]),
      previousExperimentIds: new Set(["exp-1", "exp-2"]),
      currentExperimentIds: new Set(["exp-1", "exp-2", "exp-3"]),
    });

    expect(next).toEqual(new Set(["exp-1"]));
  });
});

describe("toggle helpers", () => {
  it("toggles experiment selection", () => {
    expect(toggleExperimentSelection(new Set(["exp-1"]), "exp-2")).toEqual(
      new Set(["exp-1", "exp-2"])
    );
    expect(toggleExperimentSelection(new Set(["exp-1"]), "exp-1")).toEqual(new Set());
  });

  it("toggles hidden metrics and artifacts", () => {
    expect(toggleHiddenMetric(new Set(), "train/loss")).toEqual(new Set(["train/loss"]));
    expect(toggleHiddenArtifact(new Set(), "image:train/sample")).toEqual(
      new Set(["image:train/sample"])
    );
  });
});
