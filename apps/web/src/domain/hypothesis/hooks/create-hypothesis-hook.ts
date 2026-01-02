import { useMutation, useQueryClient } from "@tanstack/react-query";
import { hypothesisService } from "../services";
import { Hypothesis } from "../types";
import { InsertHypothesis } from "../types/dto";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export interface UseCreateHypothesisOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseCreateHypothesisResult {
    createHypothesis: (data: InsertHypothesis, options?: UseCreateHypothesisOptions) => Promise<Hypothesis>;
    isPending: boolean;
}

export function useCreateHypothesis(
    projectId?: string,
    options?: UseCreateHypothesisOptions
): UseCreateHypothesisResult {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    const mutation = useMutation({
        mutationFn: async (data: InsertHypothesis) => {
            return hypothesisService.createHypothesis(data);
        },
        onSuccess: () => {
            if (projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.HYPOTHESES.BY_PROJECT(projectId)] });
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.HYPOTHESES.RECENT(projectId)] });
            }
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DASHBOARD.STATS] });
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
            toast({
                title: "Hypothesis created",
                description: "Your new hypothesis has been created successfully.",
            });
            options?.onSuccess?.();
        },
        onError: (error: Error) => {
            toast({
                title: "Error",
                description: "Failed to create hypothesis. Please try again.",
                variant: "destructive",
            });
            options?.onError?.(error);
        },
    });

    return {
        createHypothesis: mutation.mutateAsync,
        isPending: mutation.isPending,
    };
}

