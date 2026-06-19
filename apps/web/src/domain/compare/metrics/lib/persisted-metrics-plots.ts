import { loadCompareString, saveCompareString } from "@/domain/compare/hooks/use-experiment-data-compare-layout";
import {
  DEFAULT_COMPARE_PLOT_HEIGHT,
  DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE,
  DEFAULT_COMPARE_PLOT_POINT_PADDING,
  type ComparePlotConfig,
  type PlotMetricSeries,
} from "../types/metrics-compare";

const STORAGE_KEY = "metrics-plots";

export function loadPersistedMetricsComparePlots(scope: string): ComparePlotConfig[] {
  try {
    const parsed = JSON.parse(loadCompareString(scope, STORAGE_KEY, "[]")) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((item) => {
      const plot = sanitizeMetricPlot(item);
      return plot ? [plot] : [];
    });
  } catch {
    return [];
  }
}

export function savePersistedMetricsComparePlots(scope: string, plots: ComparePlotConfig[]): void {
  saveCompareString(scope, STORAGE_KEY, JSON.stringify(plots));
}

function sanitizeMetricPlot(value: unknown): ComparePlotConfig | null {
  if (!isRecord(value) || typeof value.id !== "string") return null;
  const series = Array.isArray(value.series)
    ? value.series.flatMap((item) => {
        const sanitized = sanitizeSeries(item);
        return sanitized ? [sanitized] : [];
      })
    : [];

  return {
    id: value.id,
    series,
    nameLabelAngle: finiteNumber(value.nameLabelAngle, -25),
    nameLabelFontSize: finiteNumber(value.nameLabelFontSize, DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE),
    pointPadding: finiteNumber(value.pointPadding, DEFAULT_COMPARE_PLOT_POINT_PADDING),
    yMin: nullableNumber(value.yMin),
    yMax: nullableNumber(value.yMax),
    plotHeight: finiteNumber(value.plotHeight, DEFAULT_COMPARE_PLOT_HEIGHT),
  };
}

function sanitizeSeries(value: unknown): PlotMetricSeries | null {
  if (!isRecord(value)) return null;
  if (typeof value.id !== "string" || typeof value.name !== "string" || typeof value.color !== "string") {
    return null;
  }
  return {
    id: value.id,
    name: value.name,
    label: typeof value.label === "string" ? value.label : null,
    color: value.color,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function finiteNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function nullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
