import type { SelectiveMetricKey } from "@/domain/metrics/types";

export type PlotMetricSeries = {
  id: string;
  name: string;
  label: string | null;
  color: string;
};

export type ComparePlotConfig = {
  id: string;
  series: PlotMetricSeries[];
  /** Degrees; 0 = horizontal, negative = tilt down (Recharts XAxis convention). */
  nameLabelAngle: number;
  /** Font size (px) for experiment names, metric legend, and Y-axis tick labels. */
  nameLabelFontSize: number;
  /** Horizontal padding (px) at plot edges; increases space around experiment points. */
  pointPadding: number;
  /** Optional Y-axis lower bound; null/undefined = auto from data */
  yMin?: number | null;
  /** Optional Y-axis upper bound; null/undefined = auto from data */
  yMax?: number | null;
  /** Plot body height in px (excludes x-axis label area) */
  plotHeight?: number;
};

export const DEFAULT_COMPARE_PLOT_NAME_LABEL_ANGLE = -25;
export const DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE = 11;
export const MIN_COMPARE_PLOT_NAME_LABEL_FONT_SIZE = 8;
export const MAX_COMPARE_PLOT_NAME_LABEL_FONT_SIZE = 18;
export const DEFAULT_COMPARE_PLOT_POINT_PADDING = 12;
export const MAX_COMPARE_PLOT_POINT_PADDING = 64;
export const DEFAULT_COMPARE_PLOT_HEIGHT = 168;
export const MIN_COMPARE_PLOT_HEIGHT = 120;
export const MAX_COMPARE_PLOT_HEIGHT = 480;
/** Number of evenly spaced Y-axis ticks (and horizontal grid lines). */
export const DEFAULT_COMPARE_PLOT_Y_TICK_COUNT = 5;

export type MetricNameOption = SelectiveMetricKey & {
  displayName: string;
};
