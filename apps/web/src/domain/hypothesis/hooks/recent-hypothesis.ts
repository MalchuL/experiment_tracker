import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useQuery } from "@tanstack/react-query";
import { hypothesisService } from "../services";
import { Hypothesis } from "../types";
import { useMemo } from "react";

export interface RecentHypothesisHookResult {
    hypotheses: Hypothesis[];
    recentHypothesesIsLoading: boolean;
}

export function useRecentHypothesis(projectId?: string, limit?: number | undefined, offset?: number | undefined): RecentHypothesisHookResult {
    const { data: hypotheses, isLoading } = useQuery<Hypothesis[]>({
        queryKey: [QUERY_KEYS.HYPOTHESES.RECENT(projectId!, limit, offset)],
        queryFn: () => hypothesisService.getRecent(projectId!, limit, offset),
        enabled: Boolean(projectId)
    });
    const hypothesesCached = useMemo(() => {
        return hypotheses || [];
    }, [hypotheses]);
    return { hypotheses: hypothesesCached, recentHypothesesIsLoading: isLoading };
}