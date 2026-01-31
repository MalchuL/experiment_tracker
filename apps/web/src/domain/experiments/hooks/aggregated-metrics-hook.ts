import { useQuery } from "@tanstack/react-query";
import { projectsService } from "@/domain/projects/services";
import { Metric } from "@/domain/metrics/types";
import { useMemo } from "react";

export interface UseAggregatedMetricsResult {
    aggregatedMetricsByExperiment: Record<string, Metric[]>;
    aggregatedMetricsPlain: Metric[];
    isLoading: boolean;
    isFetching: boolean;
    refetch: () => Promise<unknown>;
}

export interface UseAggregatedMetricsQueryOptions {
    refetchInterval?: number | false;
}

export function useAggregatedMetrics(
    projectId?: string,
    options?: UseAggregatedMetricsQueryOptions
): UseAggregatedMetricsResult {
    const { data: aggregatedMetrics, isLoading, isFetching, refetch } = useQuery<Metric[]>({
        queryKey: projectId ? [`projects/${projectId}/metrics`] : [],
        queryFn: () => projectsService.getMetrics(projectId!),
        enabled: !!projectId,
        refetchInterval: options?.refetchInterval,
    });
    const aggregatedMetricsByExperiment = useMemo(() => {
        if (!aggregatedMetrics) return {};
        return aggregatedMetrics.reduce((acc: Record<string, Metric[]>, metric) => {
            if (!acc[metric.experimentId]) {
                acc[metric.experimentId] = [];
            }
            acc[metric.experimentId].push(metric);
            return acc;
        }, {} as Record<string, Metric[]>);
    }, [aggregatedMetrics]);

    const aggregatedMetricsPlain = useMemo(() => {
        return aggregatedMetrics || [];
    }, [aggregatedMetrics]);

    return {
        aggregatedMetricsByExperiment,
        aggregatedMetricsPlain,
        isLoading,
        isFetching,
        refetch,
    };
}


