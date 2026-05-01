import { useMemo } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentScalarsPoints } from "@/domain/scalars/types";
import { applySmoothing } from "@/domain/scalars/utils";

export interface ScalarMetricItem {
  name: string;
}

export interface UseScalarsDataModelParams {
  experiments: Experiment[];
  scalars: ExperimentScalarsPoints[];
  selectedExperimentIds: Set<string>;
  hiddenMetrics: Set<string>;
  smoothing: number;
  soloMode: boolean;
  chosenExperimentId: string | null;
  /** When set, selected experiments follow this order (e.g. URL order on Details page). */
  experimentDisplayOrder?: string[] | null;
}

export function useScalarsDataModel({
  experiments,
  scalars,
  selectedExperimentIds,
  hiddenMetrics,
  smoothing,
  soloMode,
  chosenExperimentId,
  experimentDisplayOrder,
}: UseScalarsDataModelParams) {
  const sortedExperiments = useMemo(() => {
    return [...experiments].sort((a, b) => {
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }, [experiments]);

  const allLoggedMetricNames = useMemo(() => {
    const metricSet = new Set<string>();
    scalars.forEach((experimentScalars) => {
      Object.keys(experimentScalars.scalars || {}).forEach((name) => metricSet.add(name));
    });
    return Array.from(metricSet).sort();
  }, [scalars]);

  const visibleMetrics = useMemo<ScalarMetricItem[]>(() => {
    if (allLoggedMetricNames.length === 0) return [];
    return allLoggedMetricNames.filter((name) => !hiddenMetrics.has(name)).map((name) => ({ name }));
  }, [allLoggedMetricNames, hiddenMetrics]);

  const selectedExperiments = useMemo(() => {
    const filtered = sortedExperiments.filter((experiment) =>
      selectedExperimentIds.has(experiment.id)
    );
    if (!experimentDisplayOrder?.length) {
      return filtered;
    }
    const idx = new Map(experimentDisplayOrder.map((id, i) => [id, i]));
    return [...filtered].sort(
      (a, b) => (idx.get(a.id) ?? 999) - (idx.get(b.id) ?? 999)
    );
  }, [sortedExperiments, selectedExperimentIds, experimentDisplayOrder]);

  const visibleExperiments = useMemo(() => {
    if (soloMode && chosenExperimentId) {
      return sortedExperiments.filter((experiment) => experiment.id === chosenExperimentId);
    }
    return selectedExperiments;
  }, [soloMode, chosenExperimentId, sortedExperiments, selectedExperiments]);

  const chartDataByMetric = useMemo(() => {
    const result: Record<string, Array<Record<string, number | null>>> = {};
    if (scalars.length === 0 || visibleExperiments.length === 0) return result;

    const scalarsByExperiment = new Map(scalars.map((entry) => [entry.experiment_id, entry.scalars]));
    for (const metric of visibleMetrics) {
      const stepMap = new Map<number, Record<string, number | null>>();
      visibleExperiments.forEach((experiment) => {
        const experimentScalars = scalarsByExperiment.get(experiment.id);
        const series = experimentScalars?.[metric.name];
        if (!series || series.x.length === 0 || series.y.length === 0) return;
        const smoothedValues = applySmoothing(series.y, smoothing);
        series.x.forEach((step, i) => {
          const existing = stepMap.get(step) || { step };
          existing[experiment.id] = smoothedValues[i];
          stepMap.set(step, existing);
        });
      });
      result[metric.name] = Array.from(stepMap.values()).sort(
        (a, b) => (a.step as number) - (b.step as number)
      );
    }
    return result;
  }, [scalars, visibleExperiments, visibleMetrics, smoothing]);

  return {
    sortedExperiments,
    allLoggedMetricNames,
    visibleMetrics,
    selectedExperiments,
    visibleExperiments,
    chartDataByMetric,
  };
}
