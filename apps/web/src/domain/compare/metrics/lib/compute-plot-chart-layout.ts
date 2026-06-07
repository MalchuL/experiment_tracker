import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";
import type { MetricsPlotChartPoint } from "./build-metrics-plot-data";

const MIN_Y_AXIS_WIDTH = 32;
const CHAR_WIDTH_PX = 5.5;
/** Tighter estimate for horizontal label extent (proportional 11px font). */
const LABEL_CHAR_WIDTH_PX = 5;
const MIN_X_AXIS_HEIGHT = 24;
const BASE_PLOT_HEIGHT = 168;
const TICK_FONT_SIZE_PX = 11;
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

export function computeComparePlotChartLayout(
  experimentNames: string[],
  chartData: MetricsPlotChartPoint[],
  seriesIds: string[],
  nameLabelAngle: number,
  pointPadding: number
): ComparePlotChartLayout {
  const maxNameLen = Math.max(0, ...experimentNames.map((name) => name.length));
  const xAxisHeight = computeXAxisHeight(maxNameLen, nameLabelAngle);

  const values: number[] = [];
  for (const row of chartData) {
    for (const id of seriesIds) {
      const value = row[id];
      if (typeof value === "number" && Number.isFinite(value)) {
        values.push(value);
      }
    }
  }

  const formattedLengths = values.map((value) => formatMetricScalarForDisplay(value).length);
  const maxValueLabelLen = formattedLengths.length > 0 ? Math.max(...formattedLengths) : 1;
  const yAxisWidth = Math.max(
    MIN_Y_AXIS_WIDTH,
    Math.ceil(maxValueLabelLen * CHAR_WIDTH_PX)
  );

  const firstNameLen = experimentNames[0]?.length ?? 0;
  const lastNameLen = experimentNames[experimentNames.length - 1]?.length ?? 0;
  const chartMarginHorizontal = {
    left: computeHorizontalLabelInset(firstNameLen, nameLabelAngle, "first"),
    right: computeHorizontalLabelInset(lastNameLen, nameLabelAngle, "last"),
  };

  const chartHeight = BASE_PLOT_HEIGHT + xAxisHeight;

  return {
    xAxisHeight,
    yAxisWidth,
    chartHeight,
    xAxisPadding: computeXAxisPadding(pointPadding),
    chartMarginHorizontal,
  };
}

function computeXAxisHeight(maxNameLen: number, angleDeg: number): number {
  const absAngle = Math.abs(angleDeg);
  const labelWidthPx = maxNameLen * CHAR_WIDTH_PX;

  if (absAngle >= 89) {
    return Math.max(MIN_X_AXIS_HEIGHT, Math.ceil(labelWidthPx + TICK_FONT_SIZE_PX + AXIS_PADDING_PX));
  }

  const angleRad = (absAngle * Math.PI) / 180;
  const verticalExtent =
    Math.abs(Math.sin(angleRad)) * labelWidthPx +
    Math.abs(Math.cos(angleRad)) * TICK_FONT_SIZE_PX;

  return Math.max(MIN_X_AXIS_HEIGHT, Math.ceil(verticalExtent + AXIS_PADDING_PX));
}

/** Reserve horizontal chart margin so first/last tick labels are not clipped. */
export function computeHorizontalLabelInset(
  nameLen: number,
  angleDeg: number,
  position: "first" | "last"
): number {
  if (nameLen <= 0) return 0;

  const labelWidth = nameLen * LABEL_CHAR_WIDTH_PX;
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
      inset = labelWidth * cos + TICK_FONT_SIZE_PX * sin;
    } else {
      return 0;
    }
  } else if (position === "last") {
    inset = labelWidth * cos + TICK_FONT_SIZE_PX * sin;
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
