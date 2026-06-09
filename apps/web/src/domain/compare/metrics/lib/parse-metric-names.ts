import type { SelectiveMetricKey } from "@/domain/metrics/types";
import { formatMetricLabel } from "@/lib/metrics/format-metric-label";
import type { MetricNameOption } from "../types/metrics-compare";

/** Map snapshot metric names + active label filter to selective batch keys. */
export function metricNamesToSelectiveKeys(
  metricNames: string[],
  activeLabel: string
): SelectiveMetricKey[] {
  const label = activeLabel === "" ? null : activeLabel;
  return metricNames.map((name) => ({ name, label }));
}

export function metricNamesToOptions(
  metricNames: string[],
  activeLabel: string
): MetricNameOption[] {
  return metricNamesToSelectiveKeys(metricNames, activeLabel).map((key) => ({
    ...key,
    displayName: formatMetricLabel(key.name, key.label),
  }));
}

export function selectiveKeyEquals(
  a: SelectiveMetricKey,
  b: SelectiveMetricKey
): boolean {
  return a.name === b.name && (a.label ?? null) === (b.label ?? null);
}
