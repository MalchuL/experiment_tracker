import type { ChartDomain, ScalarHoverMode } from "@/domain/scalars/types";

export type ScalarComparePlotConfig = {
  id: string;
  metricName: string | null;
  maxPointsDraft: string;
  appliedMaxPoints: number;
  smoothing: number;
  domain: ChartDomain | null;
  plotHeight: number;
  hoverMode: ScalarHoverMode;
  stepMinDraft: string;
  stepMin: number | null;
  stepMaxDraft: string;
  stepMax: number | null;
};

export type ScalarMetricOption = {
  name: string;
  displayName: string;
};

export const DEFAULT_SCALAR_COMPARE_PLOT_HEIGHT = 360;
export const MIN_SCALAR_COMPARE_PLOT_HEIGHT = 320;
export const MAX_SCALAR_COMPARE_PLOT_HEIGHT = 1120;
