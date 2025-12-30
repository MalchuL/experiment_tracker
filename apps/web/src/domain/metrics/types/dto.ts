import { MetricDirectionType } from "./types";

export interface InsertMetric {
    experimentId: string;
    name: string;
    value: number;
    step?: number;
    direction?: MetricDirectionType;
  }