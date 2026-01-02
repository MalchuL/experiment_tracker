import { useQuery } from "@tanstack/react-query";
import { DashboardStats } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { projectsService } from "../services";

export interface StatsHookResult {
    stats: DashboardStats;
    statsIsLoading: boolean;
}

export function useStats() {
    const { data: stats, isLoading } = useQuery<DashboardStats>({
        queryKey: [QUERY_KEYS.DASHBOARD.STATS],
        queryFn: () => projectsService.getDashboardStats(),
    });
    return { stats, statsIsLoading: isLoading };
}