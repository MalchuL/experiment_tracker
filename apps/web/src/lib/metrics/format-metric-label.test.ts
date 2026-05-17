import { describe, expect, it } from "vitest";
import { type ProjectMetric } from "@/domain/projects/types";
import { displayMetricsForApiSave, trackedToDisplayKey } from "./format-metric-label";

const trackedMetrics: ProjectMetric[] = [
  { name: "loss", direction: "minimize", aggregation: "last", label: null },
  { name: "acc", direction: "maximize", aggregation: "last", label: "val" },
  { name: "f1", direction: "maximize", aggregation: "last", label: "macro" },
];

describe("displayMetricsForApiSave", () => {
  it("preserves drag order when all tracked metrics are selected", () => {
    const reorderedAll = [
      trackedToDisplayKey(trackedMetrics[2]),
      trackedToDisplayKey(trackedMetrics[0]),
      trackedToDisplayKey(trackedMetrics[1]),
    ];

    expect(displayMetricsForApiSave(trackedMetrics, reorderedAll)).toEqual(reorderedAll);
  });

  it("keeps partial selections unchanged", () => {
    const partial = [trackedToDisplayKey(trackedMetrics[1])];

    expect(displayMetricsForApiSave(trackedMetrics, partial)).toEqual(partial);
  });
});
