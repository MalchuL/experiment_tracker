import { describe, expect, it } from "vitest";
import {
  chunkSelectiveRequestValues,
  findTopMetric,
  groupMetricsByExperiment,
  toSelectiveMetricKeys,
  toSelectiveTopMetricKeys,
} from "./selective-metrics";

describe("selective metrics helpers", () => {
  it("chunks experiment ids at the backend request limit", () => {
    const ids = Array.from({ length: 201 }, (_, index) => `experiment-${index}`);
    expect(chunkSelectiveRequestValues(ids).map((chunk) => chunk.length)).toEqual([100, 100, 1]);
  });

  it("deduplicates exact metric keys before requests", () => {
    expect(
      toSelectiveMetricKeys([
        { name: "loss", label: null, aggregation: "best", direction: "minimize" },
        { name: "loss", label: null, aggregation: "last", direction: "maximize" },
        { name: "loss", label: "validation", aggregation: "best", direction: "minimize" },
      ]),
    ).toEqual([
      { name: "loss", label: null },
      { name: "loss", label: "validation" },
    ]);
  });

  it("includes direction in top metric request keys", () => {
    expect(
      toSelectiveTopMetricKeys([
        { name: "loss", label: "validation", aggregation: "best", direction: "minimize" },
      ]),
    ).toEqual([
      { name: "loss", label: "validation", direction: "minimize" },
    ]);
  });

  it("groups selective responses by experiment id", () => {
    const metrics = [
      { id: "m1", experimentId: "e1", name: "loss", label: null, value: 1, createdAt: "" },
      { id: "m2", experimentId: "e2", name: "loss", label: null, value: 2, createdAt: "" },
      { id: "m3", experimentId: "e1", name: "score", label: "val", value: 3, createdAt: "" },
    ];
    expect(groupMetricsByExperiment(metrics)).toEqual({
      e1: [metrics[0], metrics[2]],
      e2: [metrics[1]],
    });
  });

  it("matches rank by experiment id and exact metric label", () => {
    const topMetrics = [
      { experimentId: "e1", name: "loss", label: "train", position: 1, value: 0.1 },
      { experimentId: "e1", name: "loss", label: null, position: 2, value: 0.2 },
    ];
    expect(findTopMetric(topMetrics, "e1", { name: "loss", label: null })?.position).toBe(2);
    expect(findTopMetric(topMetrics, "e2", { name: "loss", label: null })).toBeUndefined();
  });
});
