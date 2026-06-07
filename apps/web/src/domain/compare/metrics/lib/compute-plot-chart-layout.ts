import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";
import {
  DEFAULT_COMPARE_PLOT_HEIGHT,
  DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE,
  DEFAULT_COMPARE_PLOT_Y_TICK_COUNT,
} from "../types/metrics-compare";
import type { MetricsPlotChartPoint } from "./build-metrics-plot-data";

const MIN_Y_AXIS_WIDTH = 32;
/** Per-character width for Y-axis value labels at the default 11px font size. */
const BASE_Y_VALUE_CHAR_WIDTH_PX = 5.5;
/** Tighter estimate for horizontal label extent (proportional 11px font). */
/** Per-character width at the default 11px experiment-name font size. */
const BASE_LABEL_CHAR_WIDTH_PX = 5;
const MIN_X_AXIS_HEIGHT = 24;
const AXIS_PADDING_PX = 4;
const LABEL_INSET_BUFFER_PX = 0;
/** Shave computed inset — char width is conservative. */
const LABEL_INSET_TIGHTEN = 0.82;

export type ComparePlotChartLayout = {
  xAxisHeight: number;
  yAxisWidth: number;
  chartHeight: number;
  xAxisPadding: { left: number; right: number };
  chartMarginHorizontal: { left: number; right: number };
};

export type ComparePlotYDomainResult = {
  domain: [number, number];
  yMin: number | null;
  yMax: number | null;
};

export function collectPlotNumericValues(
  chartData: MetricsPlotChartPoint[],
  seriesIds: string[]
): number[] {
  const values: number[] = [];
  for (const row of chartData) {
    for (const id of seriesIds) {
      const value = row[id];
      if (typeof value === "number" && Number.isFinite(value)) {
        values.push(value);
      }
    }
  }
  return values;
}

export function computeAutoYBounds(values: number[]): [number, number] {
  if (values.length === 0) {
    return [0, 1];
  }

  const min = Math.min(...values);
  const max = Math.max(...values);

  if (min === max) {
    const magnitude = Math.max(Math.abs(min), 1);
    const pad = Math.max(1, magnitude * 0.05);
    return [min - pad, max + pad];
  }

  const span = max - min;
  const pad = span * 0.05;
  return [min - pad, max + pad];
}

export function parseYBoundInput(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function resolveYDomainFromDrafts({
  yMinDraft,
  yMaxDraft,
  yMin,
  yMax,
  values,
  lastEdited = null,
}: {
  yMinDraft: string;
  yMaxDraft: string;
  yMin?: number | null;
  yMax?: number | null;
  values: number[];
  lastEdited?: "min" | "max" | null;
}): ComparePlotYDomainResult {
  const draftMin = parseYBoundInput(yMinDraft);
  const draftMax = parseYBoundInput(yMaxDraft);
  return resolveComparePlotYDomain({
    yMin: draftMin !== undefined ? draftMin : yMin,
    yMax: draftMax !== undefined ? draftMax : yMax,
    values,
    lastEdited,
  });
}

export function resolveComparePlotYDomain({
  yMin,
  yMax,
  values,
  lastEdited = null,
}: {
  yMin?: number | null;
  yMax?: number | null;
  values: number[];
  lastEdited?: "min" | "max" | null;
}): ComparePlotYDomainResult {
  const autoBounds = computeAutoYBounds(values);
  let resolvedMin = yMin ?? null;
  let resolvedMax = yMax ?? null;

  if (resolvedMin === null) {
    resolvedMin = autoBounds[0];
  }
  if (resolvedMax === null) {
    resolvedMax = autoBounds[1];
  }

  if (resolvedMin > resolvedMax) {
    if (lastEdited === "max") {
      resolvedMin = resolvedMax - 1;
    } else {
      resolvedMax = resolvedMin + 1;
    }
  }

  return {
    domain: [resolvedMin, resolvedMax],
    yMin: yMin ?? null,
    yMax: yMax ?? null,
  };
}

/** Evenly spaced ticks from domain min to domain max (inclusive). */
export function computeUniformYTicks(
  domain: [number, number],
  tickCount: number = DEFAULT_COMPARE_PLOT_Y_TICK_COUNT
): number[] {
  const [min, max] = domain;
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [0, 1];
  }
  if (tickCount < 2) {
    return [min, max];
  }
  if (min === max) {
    return [min];
  }

  const span = max - min;
  const step = span / (tickCount - 1);
  return Array.from({ length: tickCount }, (_, index) => {
    if (index === 0) {
      return min;
    }
    if (index === tickCount - 1) {
      return max;
    }
    return min + index * step;
  });
}

export function applyYRangeToChartData(
  chartData: MetricsPlotChartPoint[],
  seriesIds: string[],
  domain: [number, number]
): MetricsPlotChartPoint[] {
  const [min, max] = domain;
  return chartData.map((row) => {
    const next: MetricsPlotChartPoint = {
      experimentName: row.experimentName,
      experimentId: row.experimentId,
    };
    for (const id of seriesIds) {
      const value = row[id];
      if (typeof value === "number" && Number.isFinite(value) && value >= min && value <= max) {
        next[id] = value;
      } else {
        next[id] = null;
      }
    }
    return next;
  });
}

export function computeComparePlotChartLayout(
  experimentNames: string[],
  chartData: MetricsPlotChartPoint[],
  seriesIds: string[],
  nameLabelAngle: number,
  pointPadding: number,
  plotHeight: number = DEFAULT_COMPARE_PLOT_HEIGHT,
  nameLabelFontSize: number = DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE
): ComparePlotChartLayout {
  const maxNameLen = Math.max(0, ...experimentNames.map((name) => name.length));
  const xAxisHeight = computeXAxisHeight(maxNameLen, nameLabelAngle, nameLabelFontSize);

  const values = collectPlotNumericValues(chartData, seriesIds);

  const formattedLengths = values.map((value) => formatMetricScalarForDisplay(value).length);
  const maxValueLabelLen = formattedLengths.length > 0 ? Math.max(...formattedLengths) : 1;
  const yValueCharWidthPx =
    BASE_Y_VALUE_CHAR_WIDTH_PX *
    (nameLabelFontSize / DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE);
  const yAxisWidth = Math.max(
    MIN_Y_AXIS_WIDTH,
    Math.ceil(maxValueLabelLen * yValueCharWidthPx)
  );

  const firstNameLen = experimentNames[0]?.length ?? 0;
  const lastNameLen = experimentNames[experimentNames.length - 1]?.length ?? 0;
  const chartMarginHorizontal = {
    left: computeHorizontalLabelInset(firstNameLen, nameLabelAngle, "first", nameLabelFontSize),
    right: computeHorizontalLabelInset(lastNameLen, nameLabelAngle, "last", nameLabelFontSize),
  };

  const chartHeight = plotHeight + xAxisHeight;

  return {
    xAxisHeight,
    yAxisWidth,
    chartHeight,
    xAxisPadding: computeXAxisPadding(pointPadding),
    chartMarginHorizontal,
  };
}

function labelCharWidthPx(fontSizePx: number): number {
  const scale = fontSizePx / DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE;
  return BASE_LABEL_CHAR_WIDTH_PX * scale;
}

function computeXAxisHeight(maxNameLen: number, angleDeg: number, fontSizePx: number): number {
  const absAngle = Math.abs(angleDeg);
  const labelWidthPx = maxNameLen * labelCharWidthPx(fontSizePx);

  if (absAngle >= 89) {
    return Math.max(MIN_X_AXIS_HEIGHT, Math.ceil(labelWidthPx + fontSizePx + AXIS_PADDING_PX));
  }

  const angleRad = (absAngle * Math.PI) / 180;
  const verticalExtent =
    Math.abs(Math.sin(angleRad)) * labelWidthPx +
    Math.abs(Math.cos(angleRad)) * fontSizePx;

  return Math.max(MIN_X_AXIS_HEIGHT, Math.ceil(verticalExtent + AXIS_PADDING_PX));
}

/** Reserve horizontal chart margin so first/last tick labels are not clipped. */
export function computeHorizontalLabelInset(
  nameLen: number,
  angleDeg: number,
  position: "first" | "last",
  fontSizePx: number = DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE
): number {
  if (nameLen <= 0) return 0;

  const labelWidth = nameLen * labelCharWidthPx(fontSizePx);
  const absAngle = Math.abs(angleDeg);
  const rad = (absAngle * Math.PI) / 180;
  const sin = Math.sin(rad);
  const cos = Math.cos(rad);
  const anchor = xAxisTickTextAnchor(angleDeg);

  let inset = 0;

  if (anchor === "middle") {
    inset = labelWidth / 2;
  } else if (anchor === "end") {
    if (position === "first") {
      inset = labelWidth * cos + fontSizePx * sin;
    } else {
      return 0;
    }
  } else if (position === "last") {
    inset = labelWidth * cos + fontSizePx * sin;
  } else {
    return 0;
  }

  return tightenLabelInset(inset);
}

function tightenLabelInset(px: number): number {
  return Math.max(0, Math.round(px * LABEL_INSET_TIGHTEN + LABEL_INSET_BUFFER_PX));
}

export function xAxisTickTextAnchor(angleDeg: number): "end" | "middle" | "start" {
  if (Math.abs(angleDeg) >= 89) return "end";
  if (Math.abs(angleDeg) < 1) return "middle";
  return angleDeg < 0 ? "end" : "start";
}

export function lineChartBottomMargin(_xAxisHeight: number): number {
  return 0;
}

function computeXAxisPadding(pointPadding: number): { left: number; right: number } {
  const padding = Math.max(0, Math.round(pointPadding));
  return { left: padding, right: padding };
}
