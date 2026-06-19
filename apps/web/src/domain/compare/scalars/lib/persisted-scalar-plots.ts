import { loadCompareString, saveCompareString } from "@/domain/compare/hooks/use-experiment-data-compare-layout";
import type { ScalarHoverMode } from "@/domain/scalars/types";
import {
  DEFAULT_SCALAR_COMPARE_PLOT_HEIGHT,
  type ScalarComparePlotConfig,
} from "../types";

const STORAGE_KEY = "scalar-plots";
const HOVER_MODES: ScalarHoverMode[] = ["compare", "visible", "nearest"];

export function loadPersistedScalarComparePlots(
  scope: string,
  defaultMaxPoints: number
): ScalarComparePlotConfig[] {
  try {
    const parsed = JSON.parse(loadCompareString(scope, STORAGE_KEY, "[]")) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((item) => {
      const plot = sanitizeScalarPlot(item, defaultMaxPoints);
      return plot ? [plot] : [];
    });
  } catch {
    return [];
  }
}

export function savePersistedScalarComparePlots(
  scope: string,
  plots: ScalarComparePlotConfig[],
  defaultMaxPoints: number
): void {
  saveCompareString(
    scope,
    STORAGE_KEY,
    JSON.stringify(plots.map((plot) => serializeScalarPlot(plot, defaultMaxPoints)))
  );
}

function serializeScalarPlot(
  plot: ScalarComparePlotConfig,
  defaultMaxPoints: number
): ScalarComparePlotConfig {
  const appliedMaxPoints = Math.min(plot.appliedMaxPoints, defaultMaxPoints);
  return {
    ...plot,
    appliedMaxPoints,
    maxPointsDraft: String(Math.min(positiveInteger(plot.maxPointsDraft, appliedMaxPoints), defaultMaxPoints)),
    stepMinDraft: optionalIntegerDraft(plot.stepMinDraft, plot.stepMin),
    stepMaxDraft: optionalIntegerDraft(plot.stepMaxDraft, plot.stepMax),
    domain: null,
  };
}

function sanitizeScalarPlot(value: unknown, defaultMaxPoints: number): ScalarComparePlotConfig | null {
  if (!isRecord(value) || typeof value.id !== "string") return null;
  const appliedMaxPoints = clampPositiveInteger(value.appliedMaxPoints, defaultMaxPoints, defaultMaxPoints);
  const stepMin = nullableInteger(value.stepMin);
  const stepMax = nullableInteger(value.stepMax);

  return {
    id: value.id,
    metricName: typeof value.metricName === "string" ? value.metricName : null,
    maxPointsDraft: String(positiveInteger(value.maxPointsDraft, appliedMaxPoints)),
    appliedMaxPoints,
    smoothing: clampNumber(value.smoothing, 0, 0.99, 0),
    domain: null,
    plotHeight: clampPositiveInteger(
      value.plotHeight,
      DEFAULT_SCALAR_COMPARE_PLOT_HEIGHT,
      Number.POSITIVE_INFINITY
    ),
    hoverMode: HOVER_MODES.includes(value.hoverMode as ScalarHoverMode)
      ? (value.hoverMode as ScalarHoverMode)
      : "compare",
    stepMinDraft: optionalIntegerDraft(value.stepMinDraft, stepMin),
    stepMin,
    stepMaxDraft: optionalIntegerDraft(value.stepMaxDraft, stepMax),
    stepMax,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function clampPositiveInteger(value: unknown, fallback: number, max: number): number {
  const parsed = typeof value === "string" ? Number(value) : value;
  if (typeof parsed !== "number" || !Number.isFinite(parsed) || parsed < 1) return fallback;
  return Math.min(Math.floor(parsed), Math.floor(max));
}

function positiveInteger(value: unknown, fallback: number): number {
  const parsed = typeof value === "string" ? Number(value) : value;
  if (typeof parsed !== "number" || !Number.isFinite(parsed) || parsed < 1) return fallback;
  return Math.floor(parsed);
}

function nullableInteger(value: unknown): number | null {
  const parsed = typeof value === "string" ? Number(value) : value;
  if (typeof parsed !== "number" || !Number.isFinite(parsed)) return null;
  return Math.floor(parsed);
}

function optionalIntegerDraft(value: unknown, fallback: number | null): string {
  const parsed = nullableInteger(value);
  if (parsed !== null) return String(parsed);
  return fallback === null ? "" : String(fallback);
}

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}
