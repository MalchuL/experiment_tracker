import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReadonlyURLSearchParams } from "next/navigation";
import type { Experiment } from "@/domain/experiments/types";
import {
  decodeLegacyNumberSelection,
  decodeStringSelection,
  encodeStringSelection,
} from "@/domain/scalars/utils";

/**
 * URL-backed UI state for the project scalars page.
 *
 * Query params (see ``buildQueryString``):
 * - ``exp`` — selected experiment ids (encoded list). Omitted when **every** experiment is selected.
 * - ``met`` — names of metrics **hidden** from charts (inverted semantics vs checkbox “visible”).
 * - ``s`` — smoothing slider in ``[0, 1]``.
 *
 * Initialization waits until experiments exist; if the URL references ``met`` but scalar columns are
 * not loaded yet (``allLoggedMetricNames`` empty), init defers so metric indices resolve correctly.
 *
 * After init, selection is synced back to the URL via ``history.replaceState`` (no full navigation).
 *
 * When the experiments list **grows** (poll / paging) while the user previously had **every**
 * experiment selected, selection is extended to new ids so checkboxes stay consistent with
 * “select all” semantics (see ``experimentsSnapshotRef`` effect).
 */
interface UseScalarsQueryStateParams {
  projectId?: string;
  searchParams: ReadonlyURLSearchParams;
  experiments: Experiment[];
  allLoggedMetricNames: string[];
}

/**
 * Owns smoothing, selected experiments, hidden-metrics sets, and bidirectional sync with the
 * scalars page URL for shareable views.
 */
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

  /** Last known experiment id set — used to detect “all experiments selected” when the list grows (poll / infinite scroll). */
  const experimentsSnapshotRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    experimentsSnapshotRef.current = new Set();
  }, [projectId]);

  /**
   * Applies URLSearchParams to React state. Supports legacy numeric indices in ``exp``/``met`` for
   * older bookmarks; filters unknown ids/names against the current experiments list and metric names.
   */
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

  /* One-shot hydration from ``searchParams`` once experiments (and metrics when needed) are ready. */
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

  /**
   * Keeps selection aligned when ``experiments`` gains rows: drops stale ids, and if the selection
   * matched the **full previous** id set, expands to the full **current** set (new runs stay selected).
   */
  useEffect(() => {
    if (!initialized || experiments.length === 0) return;

    const currentIds = new Set(experiments.map((e) => e.id));
    const prevIds = experimentsSnapshotRef.current;

    setSelectedExperimentIds((selected) => {
      let next = new Set([...selected].filter((id) => currentIds.has(id)));

      const hadFullPreviousSelection =
        prevIds.size > 0 &&
        selected.size === prevIds.size &&
        [...selected].every((id) => prevIds.has(id));

      if (hadFullPreviousSelection && currentIds.size > prevIds.size) {
        next = new Set(currentIds);
      }

      return next;
    });

    experimentsSnapshotRef.current = currentIds;
  }, [experiments, initialized]);

  /** Serializes state for the URL; omits ``exp`` when all experiments are selected to keep links short. */
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

  /* Push canonical query string to the address bar when local state diverges (debounced by React batching). */
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
