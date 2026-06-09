import type { Metric } from "@/domain/metrics/types";
import type { Experiment } from "@/domain/experiments/types";
import type { SelectiveMetricKey } from "@/domain/metrics/types";
import type {
  ExperimentDataCompareColumn,
  ExperimentDataCompareRow,
} from "@/domain/compare/components/experiment-data-compare-table";
import { formatMetricLabel, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import { selectiveKeyEquals } from "./parse-metric-names";

export function buildAllLabelsCompareTableData(
  metricKeys: SelectiveMetricKey[],
  selectedExperiments: Experiment[],
  metricsByExperiment: Record<string, Metric[]>
): {
  columns: ExperimentDataCompareColumn[];
  rows: ExperimentDataCompareRow<number>[];
} {
  const columns: ExperimentDataCompareColumn[] = selectedExperiments.map((experiment) => ({
    id: experiment.id,
    label: experiment.name,
  }));

  const rows: ExperimentDataCompareRow<number>[] = metricKeys.map((key) => ({
    id: projectMetricKeyString(key),
    label: formatMetricLabel(key.name, key.label),
    values: selectedExperiments.map((experiment) => {
      const expMetrics = metricsByExperiment[experiment.id] ?? [];
      const metric = expMetrics.find((m) => selectiveKeyEquals(m, key));
      return metric?.value;
    }),
  }));

  return { columns, rows };
}
