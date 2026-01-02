import { useMutation, useQueryClient } from "@tanstack/react-query";
import { hypothesisService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export interface UseDeleteHypothesisOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseDeleteHypothesisResult {
    deleteHypothesis: (hypothesisId: string, options?: UseDeleteHypothesisOptions) => Promise<void>;
    isPending: boolean;
}

export function useDeleteHypothesis(
    projectId?: string,
    options?: UseDeleteHypothesisOptions
): UseDeleteHypothesisResult {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    const mutation = useMutation({
        mutationFn: async (hypothesisId: string) => {
            return hypothesisService.deleteHypothesis(hypothesisId);
        },
        onSuccess: () => {
            if (projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.HYPOTHESES.BY_PROJECT(projectId)] });
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.HYPOTHESES.RECENT(projectId)] });
            }
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DASHBOARD.STATS] });
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
            toast({
                title: "Hypothesis deleted",
                description: "The hypothesis has been deleted.",
            });
            options?.onSuccess?.();
        },
        onError: (error: Error) => {
            toast({
                title: "Error",
                description: "Failed to delete hypothesis.",
                variant: "destructive",
            });
            options?.onError?.(error);
        },
    });

    return {
        deleteHypothesis: mutation.mutateAsync,
        isPending: mutation.isPending,
    };
}

