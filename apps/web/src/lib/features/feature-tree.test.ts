import { describe, expect, it } from "vitest";
import {
  diffFeatureTrees,
  isFeatureNodeArray,
  parseFeatureNodesJson,
} from "@/lib/features/feature-tree";

describe("feature tree utilities", () => {
  it("validates feature node arrays", () => {
    expect(isFeatureNodeArray([{ name: "training", children: [{ name: "adam" }] }])).toBe(true);
    expect(isFeatureNodeArray([{ name: "training", children: null }])).toBe(true);
    expect(isFeatureNodeArray({ name: "training" })).toBe(false);
    expect(isFeatureNodeArray([{ children: [{ name: "adam" }] }])).toBe(false);
  });

  it("parses feature JSON only when it is a feature node array", () => {
    expect(parseFeatureNodesJson('[{"name":"training"}]')).toEqual([{ name: "training" }]);
    expect(parseFeatureNodesJson('[{"name":"training","children":null}]')).toEqual([{ name: "training" }]);
    expect(() => parseFeatureNodesJson('{"name":"training"}')).toThrow();
  });

  it("matches similar names with levenshtein distance and reports additions/removals", () => {
    const diff = diffFeatureTrees(
      [
        { name: "optimizer-adam", children: [{ name: "weight-decay" }] },
        { name: "old-dataset" },
      ],
      [
        { name: "optimizer-adamw", children: [{ name: "weight-decay" }, { name: "warmup" }] },
        { name: "new-augmentation" },
      ]
    );

    expect(diff[0].status).toBe("renamed");
    expect(diff[0].children[0].status).toBe("unchanged");
    expect(diff[0].children[1].status).toBe("added");
    expect(diff[1].status).toBe("added");
    expect(diff[2].status).toBe("removed");
  });

  it("places added features between matched siblings by experiment order", () => {
    const diff = diffFeatureTrees(
      [{ name: "model" }, { name: "training" }],
      [{ name: "model" }, { name: "dataset" }, { name: "training" }]
    );

    expect(diff.map((row) => row.child?.name ?? row.parent?.name)).toEqual([
      "model",
      "dataset",
      "training",
    ]);
    expect(diff.map((row) => row.status)).toEqual(["unchanged", "added", "unchanged"]);
  });

  it("does not mark parents changed when only nested features changed", () => {
    const diff = diffFeatureTrees(
      [{ name: "training", children: [{ name: "optimizer-adam" }] }],
      [{ name: "training", children: [{ name: "optimizer-adamw" }] }]
    );

    expect(diff[0].status).toBe("unchanged");
    expect(diff[0].children[0].status).toBe("renamed");
  });

  it("collapses removed branches and expands added branches", () => {
    const diff = diffFeatureTrees(
      [
        {
          name: "artifacts",
          children: [
            { name: "checkpoint", children: [{ name: "best.pt" }] },
          ],
        },
      ],
      [
        {
          name: "training",
          children: [
            { name: "optimizer", children: [{ name: "adamw" }] },
          ],
        },
      ]
    );

    expect(diff[0].status).toBe("added");
    expect(diff[0].children[0].status).toBe("added");
    expect(diff[0].children[0].child?.name).toBe("optimizer");
    expect(diff[0].children[0].children[0].status).toBe("added");
    expect(diff[0].children[0].children[0].child?.name).toBe("adamw");
    expect(diff[1].status).toBe("removed");
    expect(diff[1].children).toEqual([]);
  });
});
