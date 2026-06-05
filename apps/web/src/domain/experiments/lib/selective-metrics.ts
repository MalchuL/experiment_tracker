import type {
  Metric,
  SelectiveMetricKey,
  SelectiveTopMetricKey,
  TopMetric,
} from "@/domain/metrics/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { displayMetricKeyEquals } from "@/lib/metrics/format-metric-label";

export const SELECTIVE_METRICS_BATCH_SIZE = 100;

export function toSelectiveMetricKeys(metrics: ProjectMetric[]): SelectiveMetricKey[] {
  const keys = new Map<string, SelectiveMetricKey>();
  for (const metric of metrics) {
    const key = { name: metric.name, label: metric.label ?? null };
    keys.set(`${key.name}::${key.label ?? ""}`, key);
  }
  return [...keys.values()];
}

export function toSelectiveTopMetricKeys(metrics: ProjectMetric[]): SelectiveTopMetricKey[] {
  const keys = new Map<string, SelectiveTopMetricKey>();
  for (const metric of metrics) {
    const key = {
      name: metric.name,
      label: metric.label ?? null,
      direction: metric.direction,
    };
    keys.set(`${key.name}::${key.label ?? ""}`, key);
  }
  return [...keys.values()];
}

export function chunkSelectiveRequestValues<T>(values: T[]): T[][] {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += SELECTIVE_METRICS_BATCH_SIZE) {
    chunks.push(values.slice(index, index + SELECTIVE_METRICS_BATCH_SIZE));
  }
  return chunks;
}

export function groupMetricsByExperiment(metrics: Metric[]): Record<string, Metric[]> {
  return metrics.reduce<Record<string, Metric[]>>((grouped, metric) => {
    (grouped[metric.experimentId] ??= []).push(metric);
    return grouped;
  }, {});
}

export function findTopMetric(
  topMetrics: TopMetric[] | undefined,
  experimentId: string,
  metric: Pick<ProjectMetric, "name" | "label">,
): TopMetric | undefined {
  return topMetrics?.find(
    (topMetric) =>
      topMetric.experimentId === experimentId &&
      displayMetricKeyEquals(topMetric, metric),
  );
}
