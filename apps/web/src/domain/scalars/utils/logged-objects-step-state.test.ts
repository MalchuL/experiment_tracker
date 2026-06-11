import { describe, expect, it } from "vitest";
import type { LoggedObjectGroups } from "@/domain/scalars/types";
import {
  applyFollowLatestObjectSteps,
  applyFollowLatestOverrideSteps,
  buildOverrideStepCatalog,
  buildStepCatalog,
} from "./logged-objects-step-state";

const objectGroups: LoggedObjectGroups = {
  image: {
    "train/sample": {
      steps: [1, 5, 10],
      byExperiment: {
        "exp-1": { 1: { lastModified: "a" }, 5: { lastModified: "b" } },
        "exp-2": { 10: { lastModified: "c" } },
      },
    },
  },
};

describe("buildStepCatalog", () => {
  it("uses type:name keys including slash-prefixed names", () => {
    expect(buildStepCatalog(objectGroups)).toEqual({
      "image:train/sample": [1, 5, 10],
    });
  });
});

describe("buildOverrideStepCatalog", () => {
  it("uses type:name:experimentId override keys", () => {
    expect(buildOverrideStepCatalog(objectGroups)).toEqual({
      "image:train/sample:exp-1": [1, 5],
      "image:train/sample:exp-2": [10],
    });
  });
});

describe("applyFollowLatestObjectSteps", () => {
  it("advances pinned-to-end sliders when new steps arrive", () => {
    const result = applyFollowLatestObjectSteps({
      catalog: { "image:train/sample": [1, 5, 10, 20] },
      previous: { "image:train/sample": 10 },
      followLatestStep: {},
    });

    expect(result.next["image:train/sample"]).toBe(20);
    expect(result.debouncedUpdates["image:train/sample"]).toBe(20);
  });

  it("does not overwrite manually pinned steps", () => {
    const result = applyFollowLatestObjectSteps({
      catalog: { "image:train/sample": [1, 5, 10, 20] },
      previous: { "image:train/sample": 5 },
      followLatestStep: { "image:train/sample": false },
    });

    expect(result.next["image:train/sample"]).toBe(5);
    expect(result.debouncedUpdates).toEqual({});
  });
});

describe("applyFollowLatestOverrideSteps", () => {
  it("advances enabled overrides that follow latest", () => {
    const result = applyFollowLatestOverrideSteps({
      catalog: { "image:train/sample:exp-1": [1, 5, 10] },
      previous: { "image:train/sample:exp-1": 5 },
      followLatestOverrideStep: { "image:train/sample:exp-1": true },
      experimentStepOverrideEnabled: { "image:train/sample:exp-1": true },
    });

    expect(result.next["image:train/sample:exp-1"]).toBe(10);
  });

  it("ignores disabled overrides", () => {
    const result = applyFollowLatestOverrideSteps({
      catalog: { "image:train/sample:exp-1": [1, 5, 10] },
      previous: { "image:train/sample:exp-1": 5 },
      followLatestOverrideStep: { "image:train/sample:exp-1": true },
      experimentStepOverrideEnabled: { "image:train/sample:exp-1": false },
    });

    expect(result.next["image:train/sample:exp-1"]).toBe(5);
    expect(result.debouncedUpdates).toEqual({});
  });
});
