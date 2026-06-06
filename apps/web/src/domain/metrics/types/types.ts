export const MetricDirection = {
  MINIMIZE: "minimize",
  MAXIMIZE: "maximize",
} as const;

export type MetricDirectionType = (typeof MetricDirection)[keyof typeof MetricDirection];

export const MetricAggregation = {
  LAST: "last",
  BEST: "best",
  AVERAGE: "average",
} as const;

export type MetricAggregationType = (typeof MetricAggregation)[keyof typeof MetricAggregation];

/** Logged metric row from the backend (Postgres). */
export interface Metric {
  id: string;
  experimentId: string;
  name: string;
  value: number;
  label: string | null;
  createdAt: string;
}

export interface MetricLabelsResponse {
  labels: string[];
  hasUnlabeled: boolean;
}

export interface UniqueMetricDimension {
  name: string;
  label: string | null;
}

export interface UniqueMetricDimensionsResponse {
  items: UniqueMetricDimension[];
}

export interface MetricsByLabelRow {
  experimentId: string;
  experimentName: string;
  /** ISO timestamp for the experiment. Omitted in older clients until backend is deployed. */
  createdAt?: string;
  /** Experiment accent color (hex), same as experiment settings. */
  color?: string;
  values: (number | null)[];
}

export interface MetricsByLabelSnapshot {
  metricNames: string[];
  rows: MetricsByLabelRow[];
  hasNext: boolean;
  total: number;
}

export interface SelectiveMetricKey {
  name: string;
  label: string | null;
}

export interface SelectiveTopMetricKey extends SelectiveMetricKey {
  direction: MetricDirectionType;
}

export interface TopMetric {
  experimentId: string;
  name: string;
  label: string | null;
  position: number;
  value: number;
}

export interface TopMetricsResponse {
  items: TopMetric[];
}
