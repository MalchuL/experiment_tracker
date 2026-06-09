import type { Metric } from "@/domain/metrics/types";
import type { Experiment } from "@/domain/experiments/types";
import { selectiveKeyEquals } from "./parse-metric-names";
import type { PlotMetricSeries } from "../types/metrics-compare";

export type MetricsPlotChartPoint = {
  experimentName: string;
  experimentId: string;
  [seriesId: string]: string | number | null;
};

export function buildMetricsPlotData(
  selectedExperiments: Pick<Experiment, "id" | "name">[],
  metricsByExperiment: Record<string, Metric[]>,
  series: PlotMetricSeries[]
): MetricsPlotChartPoint[] {
  return selectedExperiments.map((experiment) => {
    const expMetrics = metricsByExperiment[experiment.id] ?? [];
    const point: MetricsPlotChartPoint = {
      experimentName: experiment.name,
      experimentId: experiment.id,
    };
    for (const s of series) {
      const metric = expMetrics.find((m) =>
        selectiveKeyEquals(m, { name: s.name, label: s.label })
      );
      point[s.id] = metric?.value ?? null;
    }
    return point;
  });
}
