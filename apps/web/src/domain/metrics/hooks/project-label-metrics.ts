import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { projectsService } from "@/domain/projects/services";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { MetricLabelsResponse, MetricsByLabelSnapshot } from "../types";

export function useProjectMetricLabels(projectId: string | undefined) {
  return useQuery<MetricLabelsResponse>({
    queryKey: projectId ? [QUERY_KEYS.METRICS.LABELS(projectId)] : [],
    queryFn: () => projectsService.getMetricLabels(projectId!),
    enabled: !!projectId,
  });
}

export function useProjectMetricsByLabel(
  projectId: string | undefined,
  label: string | null,
  includeExperimentsWithoutMetrics: boolean
) {
  return useInfiniteQuery<MetricsByLabelSnapshot>({
    queryKey:
      projectId && label !== null
        ? [
            QUERY_KEYS.METRICS.BY_LABEL_SNAPSHOT(
              projectId,
              label,
              includeExperimentsWithoutMetrics
            ),
          ]
        : [],
    queryFn: async ({ pageParam }) => {
      return projectsService.getMetricsByLabelSnapshot(projectId!, {
        label: label!,
        includeExperimentsWithoutMetrics,
        limit: DEFAULT_PAGE_SIZE,
        offset: pageParam as number,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (last, all) => {
      if (!last.hasNext) {
        return undefined;
      }
      return all.reduce((n, p) => n + p.rows.length, 0);
    },
    enabled: !!projectId && label !== null,
  });
}
