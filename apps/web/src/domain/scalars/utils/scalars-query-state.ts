import type { Experiment } from "@/domain/experiments/types";
import {
  decodeLegacyNumberSelection,
  decodeStringSelection,
  encodeStringSelection,
  getDefaultSelectedExperimentIds,
} from "@/domain/scalars/utils";

export interface ScalarsQueryStateSnapshot {
  selectedExperimentIds: Set<string>;
  hiddenMetrics: Set<string>;
  hiddenArtifactIds: Set<string>;
  smoothing: number;
}

export function buildScalarsQueryString(
  experimentIds: Set<string>,
  hiddenMets: Set<string>,
  hiddenArtifacts: Set<string>,
  smooth: number,
  experimentsCount: number
): string {
  const params = new URLSearchParams();
  const allSelected = experimentIds.size === experimentsCount;
  if (!allSelected && experimentIds.size > 0) {
    params.set("exp", encodeStringSelection(Array.from(experimentIds)));
  }
  if (hiddenMets.size > 0) {
    params.set("met", encodeStringSelection(Array.from(hiddenMets)));
  }
  if (hiddenArtifacts.size > 0) {
    params.set("art", encodeStringSelection(Array.from(hiddenArtifacts)));
  }
  if (smooth > 0) {
    params.set("s", smooth.toFixed(2));
  }
  return params.toString();
}

export function parseScalarsQueryParams(
  params: URLSearchParams,
  experiments: Experiment[],
  allLoggedMetricNames: string[],
  allArtifactIds: string[]
): ScalarsQueryStateSnapshot {
  const expParam = params.get("exp");
  const metParam = params.get("met");
  const artParam = params.get("art");
  const smoothParam = params.get("s");

  let selectedExperimentIds: Set<string>;
  if (expParam) {
    const ids = decodeStringSelection(expParam);
    if (ids.length > 0) {
      const validIds = new Set(experiments.map((experiment) => experiment.id));
      selectedExperimentIds = new Set(ids.filter((id) => validIds.has(id)));
    } else {
      const legacyIndices = decodeLegacyNumberSelection(expParam);
      const selected = legacyIndices
        .map((index) => experiments[index]?.id)
        .filter((id): id is string => typeof id === "string");
      selectedExperimentIds = new Set(selected);
    }
  } else {
    selectedExperimentIds = new Set(getDefaultSelectedExperimentIds(experiments));
  }

  let hiddenMetrics: Set<string>;
  if (metParam) {
    const metricNames = decodeStringSelection(metParam);
    if (metricNames.length > 0) {
      const knownNames = new Set(allLoggedMetricNames);
      hiddenMetrics = new Set(metricNames.filter((name) => knownNames.has(name)));
    } else {
      const hiddenIndices = decodeLegacyNumberSelection(metParam);
      const hiddenNames = hiddenIndices
        .map((index) => allLoggedMetricNames[index])
        .filter((name): name is string => typeof name === "string");
      hiddenMetrics = new Set(hiddenNames);
    }
  } else {
    hiddenMetrics = new Set();
  }

  let hiddenArtifactIds: Set<string>;
  if (artParam) {
    const artifactIds = decodeStringSelection(artParam);
    if (artifactIds.length > 0) {
      const knownIds = new Set(allArtifactIds);
      hiddenArtifactIds = new Set(artifactIds.filter((id) => knownIds.has(id)));
    } else {
      const hiddenIndices = decodeLegacyNumberSelection(artParam);
      const hiddenIds = hiddenIndices
        .map((index) => allArtifactIds[index])
        .filter((id): id is string => typeof id === "string");
      hiddenArtifactIds = new Set(hiddenIds);
    }
  } else {
    hiddenArtifactIds = new Set();
  }

  let smoothing = 0;
  if (smoothParam) {
    const s = Number.parseFloat(smoothParam);
    if (!Number.isNaN(s) && s >= 0 && s <= 1) {
      smoothing = s;
    }
  }

  return {
    selectedExperimentIds,
    hiddenMetrics,
    hiddenArtifactIds,
    smoothing,
  };
}

export function syncSelectedExperimentsOnListGrowth(params: {
  selected: Set<string>;
  previousExperimentIds: Set<string>;
  currentExperimentIds: Set<string>;
}): Set<string> {
  let next = new Set([...params.selected].filter((id) => params.currentExperimentIds.has(id)));

  const hadFullPreviousSelection =
    params.previousExperimentIds.size > 0 &&
    params.selected.size === params.previousExperimentIds.size &&
    [...params.selected].every((id) => params.previousExperimentIds.has(id));

  if (hadFullPreviousSelection && params.currentExperimentIds.size > params.previousExperimentIds.size) {
    next = new Set(params.currentExperimentIds);
  }

  return next;
}

export function toggleExperimentSelection(selected: Set<string>, experimentId: string): Set<string> {
  const next = new Set(selected);
  if (next.has(experimentId)) {
    next.delete(experimentId);
  } else {
    next.add(experimentId);
  }
  return next;
}

export function toggleHiddenMetric(hidden: Set<string>, metricName: string): Set<string> {
  const next = new Set(hidden);
  if (next.has(metricName)) {
    next.delete(metricName);
  } else {
    next.add(metricName);
  }
  return next;
}

export function toggleHiddenArtifact(hidden: Set<string>, artifactId: string): Set<string> {
  const next = new Set(hidden);
  if (next.has(artifactId)) {
    next.delete(artifactId);
  } else {
    next.add(artifactId);
  }
  return next;
}
