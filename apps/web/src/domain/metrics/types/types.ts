export const MetricDirection = {
  MINIMIZE: "minimize",
  MAXIMIZE: "maximize",
} as const;

export type MetricDirectionType = typeof MetricDirection[keyof typeof MetricDirection];

export const MetricAggregation = {
  LAST: "last",
  BEST: "best",
  AVERAGE: "average",
} as const;

export type MetricAggregationType = typeof MetricAggregation[keyof typeof MetricAggregation];

export interface Metric {
    id: string;
    experimentId: string;
    name: string;
    value: number;
    step: number;
    direction: MetricDirectionType;
    createdAt: string;
  }