import { useInfiniteQuery } from "@tanstack/react-query";
import { projectsService } from "@/domain/projects/services";
import { Metric } from "@/domain/metrics/types";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { useEffect, useMemo } from "react";

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
    const {
        data,
        isLoading,
        isFetching,
        isFetchingNextPage,
        hasNextPage,
        fetchNextPage,
        refetch,
    } = useInfiniteQuery({
        queryKey: projectId ? [`projects/${projectId}/metrics`, { limit: DEFAULT_PAGE_SIZE }] : [],
        queryFn: ({ pageParam }) =>
            projectsService.getMetrics(projectId!, {
                limit: DEFAULT_PAGE_SIZE,
                offset: pageParam,
            }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, allPages) => {
            if (!lastPage.hasNext) {
                return undefined;
            }
            return allPages.reduce((total, page) => total + page.data.length, 0);
        },
        enabled: !!projectId,
        refetchInterval: options?.refetchInterval,
    });
    useEffect(() => {
        if (hasNextPage && !isFetchingNextPage) {
            void fetchNextPage();
        }
    }, [data?.pages.length, fetchNextPage, hasNextPage, isFetchingNextPage]);

    const aggregatedMetrics = useMemo(
        () => data?.pages.flatMap((page) => page.data) ?? [],
        [data]
    );
    const aggregatedMetricsByExperiment = useMemo(() => {
        return aggregatedMetrics.reduce((acc: Record<string, Metric[]>, metric) => {
            if (!acc[metric.experimentId]) {
                acc[metric.experimentId] = [];
            }
            acc[metric.experimentId].push(metric);
            return acc;
        }, {} as Record<string, Metric[]>);
    }, [aggregatedMetrics]);

    const aggregatedMetricsPlain = useMemo(() => {
        return aggregatedMetrics;
    }, [aggregatedMetrics]);

    return {
        aggregatedMetricsByExperiment,
        aggregatedMetricsPlain,
        isLoading,
        isFetching,
        refetch,
    };
}


