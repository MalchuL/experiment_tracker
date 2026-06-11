import { describe, expect, it } from "vitest";
import type { LoggedObjectGroups } from "@/domain/scalars/types";
import {
  buildScalarsContentTabs,
  partitionNamesByPrefixForTab,
  SCALARS_CONTENT_TAB_ID,
  visibleArtifactNamesForType,
} from "./scalars-content-layout";

const objectGroups: LoggedObjectGroups = {
  image: {
    "train/sample": { steps: [1], byExperiment: {} },
    sample: { steps: [2], byExperiment: {} },
    "val/sample": { steps: [3], byExperiment: {} },
  },
  pie: {
    "train/dist": { steps: [1], byExperiment: {} },
  },
};

describe("buildScalarsContentTabs", () => {
  it("includes scalars tab and only artifact types with visible items", () => {
    const tabs = buildScalarsContentTabs({
      visibleMetricNames: ["loss", "train/loss"],
      objectGroups,
      hiddenArtifactIds: new Set(["pie:train/dist"]),
    });

    expect(tabs.map((tab) => tab.id)).toEqual([SCALARS_CONTENT_TAB_ID, "image"]);
  });

  it("omits scalars tab when all metrics are hidden", () => {
    const tabs = buildScalarsContentTabs({
      visibleMetricNames: [],
      objectGroups,
      hiddenArtifactIds: new Set(),
    });

    expect(tabs.map((tab) => tab.id)).toEqual(["image", "pie"]);
  });
});

describe("visibleArtifactNamesForType", () => {
  it("excludes hidden artifact ids", () => {
    expect(
      visibleArtifactNamesForType(objectGroups, "image", new Set(["image:train/sample"]))
    ).toEqual(["sample", "val/sample"]);
  });
});

describe("partitionNamesByPrefixForTab", () => {
  it("partitions metric names with ungrouped first", () => {
    expect(partitionNamesByPrefixForTab(["loss", "train/loss", "val/loss"])).toEqual({
      ungrouped: ["loss"],
      groups: [
        { key: "train", items: ["train/loss"] },
        { key: "val", items: ["val/loss"] },
      ],
    });
  });
});
