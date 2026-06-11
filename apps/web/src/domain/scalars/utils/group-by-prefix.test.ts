import { describe, expect, it } from "vitest";
import { groupNamesByPrefix, splitPrefixGroup } from "./group-by-prefix";

describe("splitPrefixGroup", () => {
  it("returns null group when name has no slash", () => {
    expect(splitPrefixGroup("loss")).toEqual({ group: null, leaf: "loss" });
  });

  it("splits on first slash only", () => {
    expect(splitPrefixGroup("train/val/loss")).toEqual({
      group: "train",
      leaf: "val/loss",
    });
  });
});

describe("groupNamesByPrefix", () => {
  it("keeps ungrouped names in input order at top", () => {
    const result = groupNamesByPrefix(["loss", "accuracy", "train/loss", "val/loss", "train/acc"]);
    expect(result.ungrouped).toEqual(["loss", "accuracy"]);
    expect(result.groups).toEqual([
      { key: "train", items: ["train/acc", "train/loss"] },
      { key: "val", items: ["val/loss"] },
    ]);
  });
});
