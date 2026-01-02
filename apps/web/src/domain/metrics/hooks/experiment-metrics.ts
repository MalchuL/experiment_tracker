import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useQuery } from "@tanstack/react-query";
import { Metric } from "../types";
import { metricsService } from "../services";

export interface UseExperimentMetricsResult {
    metrics: Metric[] | undefined;
    isLoading: boolean;
}

export function useExperimentMetrics(experimentId: string): UseExperimentMetricsResult {
    const { data: metrics, isLoading } = useQuery<Metric[]>({
        queryKey: [QUERY_KEYS.METRICS.GET(experimentId)],
        queryFn: () => metricsService.getByExperiment(experimentId),
        enabled: !!experimentId,
    });
    return { metrics, isLoading };
}