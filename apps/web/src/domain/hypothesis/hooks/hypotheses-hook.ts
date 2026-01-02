import { useQuery } from "@tanstack/react-query";
import { hypothesisService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { Hypothesis } from "../types";

export interface UseHypothesesResult {
    hypotheses: Hypothesis[];
    isLoading: boolean;
}

export function useHypotheses(projectId?: string): UseHypothesesResult {
    const { data: hypotheses, isLoading } = useQuery<Hypothesis[]>({
        queryKey: projectId ? [QUERY_KEYS.HYPOTHESES.BY_PROJECT(projectId)] : [],
        queryFn: () => hypothesisService.getByProject(projectId!),
        enabled: !!projectId,
        staleTime: 0,
    });

    return {
        hypotheses: hypotheses ?? [],
        isLoading,
    };
}

