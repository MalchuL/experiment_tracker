import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hypothesisService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { Hypothesis } from "../types";
import { useMemo } from "react";

export interface UseHypothesesOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseHypothesesResult {
    hypotheses: Hypothesis[];
    isLoading: boolean;
    deleteHypothesis: (hypothesisId: string, options?: UseHypothesesOptions) => Promise<void>;
    deleteIsPending: boolean;
}

export function useHypotheses(projectId?: string): UseHypothesesResult {
    const queryClient = useQueryClient();

    const { data: hypotheses, isLoading } = useQuery<Hypothesis[]>({
        queryKey: projectId ? [QUERY_KEYS.HYPOTHESES.BY_PROJECT(projectId)] : [],
        queryFn: () => hypothesisService.getByProject(projectId!),
        enabled: !!projectId,
        staleTime: 0,
    });

    const deleteMutation = useMutation({
        mutationFn: async (hypothesisId: string) => {
            return hypothesisService.deleteHypothesis(hypothesisId);
        },
        onSuccess: () => {
            if (projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.HYPOTHESES.BY_PROJECT(projectId)] });
            }    
        },
    });

    const hypothesesCached = useMemo(() => {
        return hypotheses || [];
    }, [hypotheses]);

    return {
        hypotheses: hypothesesCached,
        isLoading,
        deleteHypothesis: deleteMutation.mutateAsync,
        deleteIsPending: deleteMutation.isPending,
    };
}

