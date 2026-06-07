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
  /** Horizontal padding (px) at plot edges; increases space around experiment points. */
  pointPadding: number;
};

export const DEFAULT_COMPARE_PLOT_NAME_LABEL_ANGLE = -25;
export const DEFAULT_COMPARE_PLOT_POINT_PADDING = 12;
export const MAX_COMPARE_PLOT_POINT_PADDING = 64;

export type MetricNameOption = SelectiveMetricKey & {
  displayName: string;
};
