import { useMemo } from "react";
import { parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentScalarsPoints } from "@/domain/scalars/types";
import {
  buildChartDataByMetric,
  resolveVisibleExperiments,
} from "@/domain/scalars/utils/scalars-data-model";

export { buildChartDataByMetric, resolveVisibleExperiments } from "@/domain/scalars/utils/scalars-data-model";

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
      return parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime();
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
    return resolveVisibleExperiments({
      sortedExperiments,
      selectedExperimentIds,
      soloMode: false,
      chosenExperimentId: null,
      experimentDisplayOrder,
    });
  }, [sortedExperiments, selectedExperimentIds, experimentDisplayOrder]);

  const visibleExperiments = useMemo(() => {
    return resolveVisibleExperiments({
      sortedExperiments,
      selectedExperimentIds,
      soloMode,
      chosenExperimentId,
      experimentDisplayOrder,
    });
  }, [soloMode, chosenExperimentId, sortedExperiments, selectedExperimentIds, experimentDisplayOrder]);

  const allChartDataByMetric = useMemo(() => {
    return buildChartDataByMetric({
      scalars,
      allLoggedMetricNames,
      visibleExperiments,
      smoothing,
    });
  }, [allLoggedMetricNames, scalars, visibleExperiments, smoothing]);

  const chartDataByMetric = useMemo(() => {
    return Object.fromEntries(
      visibleMetrics.map((metric) => [metric.name, allChartDataByMetric[metric.name] ?? []])
    );
  }, [allChartDataByMetric, visibleMetrics]);

  return {
    sortedExperiments,
    allLoggedMetricNames,
    visibleMetrics,
    selectedExperiments,
    visibleExperiments,
    chartDataByMetric,
    allChartDataByMetric,
  };
}
