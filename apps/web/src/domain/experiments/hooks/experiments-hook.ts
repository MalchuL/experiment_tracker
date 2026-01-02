import { useQuery } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { Experiment } from "../types";

export interface UseExperimentsResult {
    experiments: Experiment[];
    isLoading: boolean;
}

export function useExperiments(projectId?: string): UseExperimentsResult {
    const { data: experiments, isLoading } = useQuery<Experiment[]>({
        queryKey: projectId ? [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)] : [],
        queryFn: () => experimentsService.getByProject(projectId!),
        enabled: !!projectId,
        staleTime: 0,
    });

    return {
        experiments: experiments ?? [],
        isLoading,
    };
}


