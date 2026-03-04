import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReadonlyURLSearchParams } from "next/navigation";
import type { Experiment } from "@/domain/experiments/types";
import {
  decodeLegacyNumberSelection,
  decodeStringSelection,
  encodeStringSelection,
} from "@/domain/scalars/utils";

interface UseScalarsQueryStateParams {
  projectId?: string;
  searchParams: ReadonlyURLSearchParams;
  experiments: Experiment[];
  allLoggedMetricNames: string[];
}

export function useScalarsQueryState({
  projectId,
  searchParams,
  experiments,
  allLoggedMetricNames,
}: UseScalarsQueryStateParams) {
  const [smoothing, setSmoothing] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<Set<string>>(new Set());
  const [hiddenMetrics, setHiddenMetrics] = useState<Set<string>>(new Set());

  const applySharedParams = useCallback(
    (params: URLSearchParams) => {
      try {
        const expParam = params.get("exp");
        const metParam = params.get("met");
        const smoothParam = params.get("s");

        if (expParam) {
          const ids = decodeStringSelection(expParam);
          if (ids.length > 0) {
            const validIds = new Set(experiments.map((experiment) => experiment.id));
            const selected = ids.filter((id) => validIds.has(id));
            setSelectedExperimentIds(new Set(selected));
          } else {
            const legacyIndices = decodeLegacyNumberSelection(expParam);
            const selected = legacyIndices
              .map((index) => experiments[index]?.id)
              .filter((id): id is string => typeof id === "string");
            setSelectedExperimentIds(new Set(selected));
          }
        } else {
          setSelectedExperimentIds(new Set(experiments.map((experiment) => experiment.id)));
        }

        if (metParam) {
          const metricNames = decodeStringSelection(metParam);
          if (metricNames.length > 0) {
            const knownNames = new Set(allLoggedMetricNames);
            setHiddenMetrics(new Set(metricNames.filter((name) => knownNames.has(name))));
          } else {
            const hiddenIndices = decodeLegacyNumberSelection(metParam);
            const hiddenNames = hiddenIndices
              .map((index) => allLoggedMetricNames[index])
              .filter((name): name is string => typeof name === "string");
            setHiddenMetrics(new Set(hiddenNames));
          }
        } else {
          setHiddenMetrics(new Set());
        }

        if (smoothParam) {
          const s = Number.parseFloat(smoothParam);
          if (!Number.isNaN(s) && s >= 0 && s <= 1) {
            setSmoothing(s);
            return;
          }
        }
        setSmoothing(0);
      } catch {
        setSelectedExperimentIds(new Set(experiments.map((experiment) => experiment.id)));
        setHiddenMetrics(new Set());
        setSmoothing(0);
      }
    },
    [experiments, allLoggedMetricNames]
  );

  useEffect(() => {
    if (experiments.length === 0 || initialized) return;
    const hasMetricsParam = !!searchParams.get("met");
    if (hasMetricsParam && allLoggedMetricNames.length === 0) return;
    const timer = window.setTimeout(() => {
      applySharedParams(new URLSearchParams(searchParams.toString()));
      setInitialized(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [experiments, searchParams, initialized, allLoggedMetricNames, applySharedParams]);

  const buildQueryString = useCallback(
    (experimentIds: Set<string>, hiddenMets: Set<string>, smooth: number) => {
      const params = new URLSearchParams();
      const allSelected = experimentIds.size === experiments.length;
      if (!allSelected && experimentIds.size > 0) {
        params.set("exp", encodeStringSelection(Array.from(experimentIds)));
      }
      if (hiddenMets.size > 0) {
        params.set("met", encodeStringSelection(Array.from(hiddenMets)));
      }
      if (smooth > 0) {
        params.set("s", smooth.toFixed(2));
      }
      return params.toString();
    },
    [experiments.length]
  );

  const currentQueryString = useMemo(
    () => buildQueryString(selectedExperimentIds, hiddenMetrics, smoothing),
    [buildQueryString, selectedExperimentIds, hiddenMetrics, smoothing]
  );

  useEffect(() => {
    if (!initialized || !projectId) return;
    const nextQuery = buildQueryString(selectedExperimentIds, hiddenMetrics, smoothing);
    const currentQuery = new URLSearchParams(window.location.search).toString();
    if (nextQuery === currentQuery) return;
    const basePath = `/projects/${projectId}/scalars`;
    window.history.replaceState(
      window.history.state,
      "",
      nextQuery ? `${basePath}?${nextQuery}` : basePath
    );
  }, [initialized, projectId, selectedExperimentIds, hiddenMetrics, smoothing, buildQueryString]);

  const toggleExperiment = useCallback((experimentId: string) => {
    setSelectedExperimentIds((prev) => {
      const next = new Set(prev);
      if (next.has(experimentId)) {
        next.delete(experimentId);
      } else {
        next.add(experimentId);
      }
      return next;
    });
  }, []);

  const selectAllExperiments = useCallback(() => {
    setSelectedExperimentIds(new Set(experiments.map((experiment) => experiment.id)));
  }, [experiments]);

  const clearAllExperiments = useCallback(() => {
    setSelectedExperimentIds(new Set());
  }, []);

  const toggleMetric = useCallback((metricName: string) => {
    setHiddenMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(metricName)) {
        next.delete(metricName);
      } else {
        next.add(metricName);
      }
      return next;
    });
  }, []);

  const showAllMetrics = useCallback(() => {
    setHiddenMetrics(new Set());
  }, []);

  const showOnlyMetric = useCallback(
    (metricName: string) => {
      if (allLoggedMetricNames.length === 0) return;
      setHiddenMetrics(new Set(allLoggedMetricNames.filter((name) => name !== metricName)));
    },
    [allLoggedMetricNames]
  );

  const handleRestoreSavedView = useCallback(
    (query: string) => {
      const normalizedQuery = query.startsWith("?") ? query.slice(1) : query;
      const params = new URLSearchParams(normalizedQuery);
      applySharedParams(params);
      if (projectId) {
        const basePath = `/projects/${projectId}/scalars`;
        window.history.replaceState(
          window.history.state,
          "",
          normalizedQuery ? `${basePath}?${normalizedQuery}` : basePath
        );
      }
    },
    [applySharedParams, projectId]
  );

  return {
    smoothing,
    setSmoothing,
    initialized,
    selectedExperimentIds,
    hiddenMetrics,
    currentQueryString,
    setSelectedExperimentIds,
    toggleExperiment,
    selectAllExperiments,
    clearAllExperiments,
    toggleMetric,
    showAllMetrics,
    showOnlyMetric,
    handleRestoreSavedView,
  };
}
