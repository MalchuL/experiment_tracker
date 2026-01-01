import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { experimentsService } from "../services/experiments-service";
import { useQuery } from "@tanstack/react-query";
import { Experiment } from "../types";

export interface RecentExperimentsHookResult {
    experiments: Experiment[];
    recentExperimentsIsLoading: boolean;
}

export function useRecentExperiments(projectId: string, limit?: number | undefined, offset?: number | undefined): RecentExperimentsHookResult {
    const { data: experiments, isLoading } = useQuery<Experiment[]>({
        queryKey: [QUERY_KEYS.EXPERIMENTS.RECENT(projectId, limit, offset)],
        queryFn: () => experimentsService.getRecent(projectId, limit, offset),
    });
    return { experiments: experiments ?? [], recentExperimentsIsLoading: isLoading };
}