import { createClientId } from "@/lib/utils";
import {
  DEFAULT_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH,
  DEFAULT_SCALAR_COMPARE_PLOT_HEIGHT,
  type ScalarComparePlotConfig,
} from "../types";

export function createScalarComparePlotConfig(defaultMaxPoints: number): ScalarComparePlotConfig {
  return {
    id: createClientId(),
    metricName: null,
    maxPointsDraft: String(defaultMaxPoints),
    appliedMaxPoints: defaultMaxPoints,
    smoothing: 0,
    domain: null,
    plotHeight: DEFAULT_SCALAR_COMPARE_PLOT_HEIGHT,
    hoverMode: "compare",
    hoverNameMaxLength: DEFAULT_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH,
    stepMinDraft: "",
    stepMin: null,
    stepMaxDraft: "",
    stepMax: null,
  };
}

export function patchScalarComparePlotConfig(
  plots: ScalarComparePlotConfig[],
  plotId: string,
  patch: Partial<ScalarComparePlotConfig>
): ScalarComparePlotConfig[] {
  return plots.map((plot) => (plot.id === plotId ? { ...plot, ...patch } : plot));
}

export function resolveCommittedMaxPoints(
  draft: string,
  currentAppliedMaxPoints: number
): { appliedMaxPoints: number; maxPointsDraft: string; changed: boolean } {
  const parsed = Number(draft);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return {
      appliedMaxPoints: currentAppliedMaxPoints,
      maxPointsDraft: String(currentAppliedMaxPoints),
      changed: false,
    };
  }

  const draftValue = Math.floor(parsed);
  return {
    appliedMaxPoints: draftValue,
    maxPointsDraft: String(draftValue),
    changed: draftValue !== currentAppliedMaxPoints,
  };
}

export function resolveCommittedStepBound(
  draft: string,
  currentAppliedStepBound: number | null
): { stepBound: number | null; stepBoundDraft: string; changed: boolean } {
  const trimmed = draft.trim();
  if (!trimmed) {
    return {
      stepBound: null,
      stepBoundDraft: "",
      changed: currentAppliedStepBound !== null,
    };
  }

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return {
      stepBound: currentAppliedStepBound,
      stepBoundDraft: currentAppliedStepBound === null ? "" : String(currentAppliedStepBound),
      changed: false,
    };
  }

  const draftValue = Math.floor(parsed);
  return {
    stepBound: draftValue,
    stepBoundDraft: String(draftValue),
    changed: draftValue !== currentAppliedStepBound,
  };
}
