import { describe, expect, it } from "vitest";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentScalarsPoints } from "@/domain/scalars/types";
import { buildChartDataByMetric, resolveVisibleExperiments } from "./scalars-data-model";

const experiments = [
  { id: "exp-old", name: "Old", createdAt: "2026-05-18T10:00:00.000Z" },
  { id: "exp-new", name: "New", createdAt: "2026-05-20T10:00:00.000Z" },
] as Experiment[];

const scalars: ExperimentScalarsPoints[] = [
  {
    experiment_id: "exp-old",
    scalars: { "train/loss": { x: [1], y: [0.5] } },
  },
  {
    experiment_id: "exp-new",
    scalars: { "train/loss": { x: [1], y: [0.1] } },
  },
];

describe("resolveVisibleExperiments", () => {
  it("drops deselected experiments from visible set", () => {
    const visible = resolveVisibleExperiments({
      sortedExperiments: experiments,
      selectedExperimentIds: new Set(["exp-old"]),
      soloMode: false,
      chosenExperimentId: null,
    });

    expect(visible.map((exp) => exp.id)).toEqual(["exp-old"]);
  });

  it("shows only chosen experiment in solo mode", () => {
    const visible = resolveVisibleExperiments({
      sortedExperiments: experiments,
      selectedExperimentIds: new Set(["exp-old", "exp-new"]),
      soloMode: true,
      chosenExperimentId: "exp-new",
    });

    expect(visible.map((exp) => exp.id)).toEqual(["exp-new"]);
  });
});

describe("buildChartDataByMetric", () => {
  it("builds per-metric chart points only for visible experiments", () => {
    const chartData = buildChartDataByMetric({
      scalars,
      allLoggedMetricNames: ["train/loss"],
      visibleExperiments: [experiments[0]!],
      smoothing: 0,
    });

    expect(chartData["train/loss"]).toEqual([
      {
        step: 1,
        "exp-old": { original: 0.5, smoothed: 0.5 },
      },
    ]);
  });
});
