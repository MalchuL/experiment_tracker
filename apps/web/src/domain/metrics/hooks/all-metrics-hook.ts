import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { metricsService } from "../services";
import { useExperiments } from "@/domain/experiments/hooks";
import type { Metric } from "../types";

export interface UseAllMetricsResult {
    allMetrics: Record<string, Metric[]> | undefined;
    isLoading: boolean;
}

export function useAllMetrics(projectId?: string): UseAllMetricsResult {
    const { experiments } = useExperiments(projectId);

    const { data: allMetrics, isLoading } = useQuery<Record<string, Metric[]>>({
        queryKey: projectId && experiments ? [`projects/${projectId}/all-metrics`, experiments.map(e => e.id)] : [],
        queryFn: async () => {
            if (!experiments || experiments.length === 0) return {};
            
            const metricsPromises = experiments.map(async (experiment) => {
                const metrics = await metricsService.getByExperiment(experiment.id);
                return { experimentId: experiment.id, metrics };
            });
            
            const results = await Promise.all(metricsPromises);
            const metricsMap: Record<string, Metric[]> = {};
            
            results.forEach(({ experimentId, metrics }) => {
                metricsMap[experimentId] = metrics;
            });
            
            return metricsMap;
        },
        enabled: !!projectId && !!experiments && experiments.length > 0,
    });

    return {
        allMetrics,
        isLoading,
    };
}

