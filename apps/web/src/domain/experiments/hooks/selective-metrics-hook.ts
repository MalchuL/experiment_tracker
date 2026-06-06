import { useQuery } from "@tanstack/react-query";
import { projectsService } from "@/domain/projects/services";
import type { Metric, TopMetric } from "@/domain/metrics/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import {
  chunkSelectiveRequestValues,
  groupMetricsByExperiment,
  toSelectiveMetricKeys,
  toSelectiveTopMetricKeys,
} from "../lib/selective-metrics";

export interface UseSelectiveProjectMetricsOptions {
  refetchInterval?: number | false;
}

export function useSelectiveProjectMetrics(
  projectId: string | undefined,
  experimentIds: string[],
  metrics: ProjectMetric[],
  options?: UseSelectiveProjectMetricsOptions,
) {
  const stableExperimentIds = [...new Set(experimentIds)].sort();
  const metricKeys = toSelectiveMetricKeys(metrics);
  const metricKeyString = metricKeys.map((metric) => `${metric.name}::${metric.label ?? ""}`).join("|");
  const enabled = Boolean(projectId && stableExperimentIds.length > 0 && metricKeys.length > 0);
  const query = useQuery<Metric[]>({
    queryKey: enabled
      ? [QUERY_KEYS.METRICS.SELECTIVE(projectId!), stableExperimentIds, metricKeyString]
      : [],
    queryFn: async () => {
      const pages = await Promise.all(
        chunkSelectiveRequestValues(stableExperimentIds).flatMap((experimentChunk) =>
          chunkSelectiveRequestValues(metricKeys).map((metricChunk) =>
            projectsService.getSelectiveMetrics(projectId!, experimentChunk, metricChunk),
          ),
        )
      );
      return pages.flatMap((page) => page.data);
    },
    enabled,
    refetchInterval: options?.refetchInterval,
  });

  return {
    metricsByExperiment: groupMetricsByExperiment(query.data ?? []),
    isLoading: enabled ? query.isLoading : false,
    isFetching: query.isFetching,
    refetch: query.refetch,
  };
}

export function useTopProjectMetrics(
  projectId: string | undefined,
  metrics: ProjectMetric[],
  options?: UseSelectiveProjectMetricsOptions,
) {
  const metricKeys = toSelectiveTopMetricKeys(metrics);
  const metricKeyString = metricKeys
    .map((metric) => `${metric.name}::${metric.label ?? ""}::${metric.direction}`)
    .join("|");
  const enabled = Boolean(projectId && metricKeys.length > 0);
  const query = useQuery<TopMetric[]>({
    queryKey: enabled ? [QUERY_KEYS.METRICS.TOP(projectId!), metricKeyString, 3] : [],
    queryFn: async () => {
      const responses = await Promise.all(
        chunkSelectiveRequestValues(metricKeys).map((metricChunk) =>
          projectsService.getTopMetrics(projectId!, metricChunk, 3),
        ),
      );
      return responses.flatMap((response) => response.items);
    },
    enabled,
    refetchInterval: options?.refetchInterval,
  });
  return {
    topMetrics: query.data ?? [],
    isFetching: query.isFetching,
    refetch: query.refetch,
  };
}
