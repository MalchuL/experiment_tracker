import { parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ExperimentScalarsPoints,
  ScalarChartPoint,
  ScalarPointValue,
} from "@/domain/scalars/types";
import { applySmoothing } from "@/domain/scalars/utils/smoothing";

export function resolveVisibleExperiments(params: {
  sortedExperiments: Experiment[];
  selectedExperimentIds: Set<string>;
  soloMode: boolean;
  chosenExperimentId: string | null;
  experimentDisplayOrder?: string[] | null;
}): Experiment[] {
  const filtered = params.sortedExperiments.filter((experiment) =>
    params.selectedExperimentIds.has(experiment.id)
  );
  const ordered = params.experimentDisplayOrder?.length
    ? [...filtered].sort(
        (a, b) =>
          (params.experimentDisplayOrder!.indexOf(a.id) ?? 999) -
          (params.experimentDisplayOrder!.indexOf(b.id) ?? 999)
      )
    : filtered;

  if (params.soloMode && params.chosenExperimentId) {
    return params.sortedExperiments.filter(
      (experiment) => experiment.id === params.chosenExperimentId
    );
  }

  return [...ordered].sort(
    (a, b) => parseISO(a.createdAt).getTime() - parseISO(b.createdAt).getTime()
  );
}

export function buildChartDataByMetric(params: {
  scalars: ExperimentScalarsPoints[];
  allLoggedMetricNames: string[];
  visibleExperiments: Experiment[];
  smoothing: number;
}): Record<string, ScalarChartPoint[]> {
  const result: Record<string, ScalarChartPoint[]> = {};
  if (params.scalars.length === 0 || params.visibleExperiments.length === 0) {
    return result;
  }

  const scalarsByExperiment = new Map(
    params.scalars.map((entry) => [entry.experiment_id, entry.scalars])
  );

  for (const metricName of params.allLoggedMetricNames) {
    const stepMap = new Map<number, ScalarChartPoint>();
    params.visibleExperiments.forEach((experiment) => {
      const experimentScalars = scalarsByExperiment.get(experiment.id);
      const series = experimentScalars?.[metricName];
      if (!series || series.x.length === 0 || series.y.length === 0) return;
      const smoothedValues = applySmoothing(series.y, params.smoothing);
      series.x.forEach((step, i) => {
        const existing = stepMap.get(step) || { step };
        const original = series.y[i];
        const smoothed = smoothedValues[i];
        if (original === undefined || smoothed === undefined) {
          return;
        }
        existing[experiment.id] = {
          original,
          smoothed,
        } satisfies ScalarPointValue;
        stepMap.set(step, existing);
      });
    });
    result[metricName] = Array.from(stepMap.values()).sort(
      (a, b) => (a.step as number) - (b.step as number)
    );
  }

  return result;
}
