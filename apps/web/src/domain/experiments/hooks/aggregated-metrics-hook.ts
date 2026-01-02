import { useQuery } from "@tanstack/react-query";
import { projectsService } from "@/domain/projects/services/projects-service";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

export interface UseAggregatedMetricsResult {
    aggregatedMetrics: Record<string, Record<string, number | null>> | undefined;
    isLoading: boolean;
}

export function useAggregatedMetrics(projectId?: string): UseAggregatedMetricsResult {
    const { data: aggregatedMetrics, isLoading } = useQuery<Record<string, Record<string, number | null>>>({
        queryKey: projectId ? [`projects/${projectId}/metrics`] : [],
        queryFn: () => projectsService.getMetrics(projectId!),
        enabled: !!projectId,
    });

    return {
        aggregatedMetrics,
        isLoading,
    };
}


