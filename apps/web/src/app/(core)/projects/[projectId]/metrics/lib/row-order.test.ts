import { describe, expect, it } from "vitest";
import {
  metricNamesFromColumnOrder,
  orderRowsByIds,
  rebuildColumnOrder,
  reorderIdSubset,
  syncExperimentRowOrder,
} from "./row-order";
import type { MetricsTableRow } from "./types";

function row(id: string, createdAt = ""): MetricsTableRow {
  return {
    experimentId: id,
    experimentName: id,
    createdAt,
    experimentColor: "#000",
    byName: {},
  };
}

describe("row-order", () => {
  it("extracts metric names from column order", () => {
    expect(
      metricNamesFromColumnOrder(["experiment", "loss", "acc", "experimentId", "createdAt"])
    ).toEqual(["loss", "acc"]);
  });

  it("rebuilds full column order from metric names", () => {
    expect(rebuildColumnOrder(["acc", "loss"])).toEqual([
      "experiment",
      "acc",
      "loss",
      "experimentId",
      "createdAt",
    ]);
  });

  it("syncs experiment row order when rows change", () => {
    expect(syncExperimentRowOrder(["b", "a"], [row("a"), row("b"), row("c")])).toEqual([
      "b",
      "a",
      "c",
    ]);
  });

  it("orders rows by visual id list", () => {
    const rows = [row("a"), row("b"), row("c")];
    expect(orderRowsByIds(rows, ["c", "a", "b"]).map((r) => r.experimentId)).toEqual([
      "c",
      "a",
      "b",
    ]);
  });

  it("reorders a subset within full order", () => {
    expect(reorderIdSubset(["a", "b", "c", "d"], ["b", "d"], "d", "b")).toEqual([
      "a",
      "d",
      "c",
      "b",
    ]);
  });
});
