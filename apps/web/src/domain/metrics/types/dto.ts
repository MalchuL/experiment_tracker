export interface InsertMetric {
  experimentId: string;
  name: string;
  value: number;
  label?: string | null;
}