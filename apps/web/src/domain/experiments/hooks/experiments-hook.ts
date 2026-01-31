import { useQuery } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { Experiment } from "../types";
import { useMemo } from "react";

export interface UseExperimentsResult {
    experiments: Experiment[];
    isLoading: boolean;
    isFetching: boolean;
    refetch: () => Promise<unknown>;
}

export interface UseExperimentsQueryOptions {
    refetchInterval?: number | false;
}

export function useExperiments(
    projectId?: string,
    options?: UseExperimentsQueryOptions
): UseExperimentsResult {
    const { data: experiments, isLoading, isFetching, refetch } = useQuery<Experiment[]>({
        queryKey: projectId ? [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)] : [],
        queryFn: () => experimentsService.getByProject(projectId!),
        enabled: !!projectId,
        staleTime: 30000, // 30 seconds
        refetchInterval: options?.refetchInterval,
    });

    const experimentsCached = useMemo(() => {
        return experiments || [];
    }, [experiments]);

    return {
        experiments: experimentsCached,
        isLoading,
        isFetching,
        refetch,
    };
}


