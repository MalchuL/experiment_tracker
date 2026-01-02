import { useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "../services/experiments-service";
import { Experiment, InsertExperiment } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export interface UseCreateExperimentOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseCreateExperimentResult {
    createExperiment: (data: InsertExperiment, options?: UseCreateExperimentOptions) => Promise<Experiment>;
    isPending: boolean;
}

export function useCreateExperiment(
    projectId?: string,
    options?: UseCreateExperimentOptions
): UseCreateExperimentResult {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    const mutation = useMutation({
        mutationFn: async (data: InsertExperiment) => {
            return experimentsService.create(data);
        },
        onSuccess: () => {
            if (projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.RECENT(projectId)] });
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)] });
            }
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DASHBOARD.STATS] });
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
            toast({
                title: "Experiment created",
                description: "Your new experiment has been created successfully.",
            });
            options?.onSuccess?.();
        },
        onError: (error: Error) => {
            toast({
                title: "Error",
                description: "Failed to create experiment.",
                variant: "destructive",
            });
            options?.onError?.(error);
        },
    });

    return {
        createExperiment: mutation.mutateAsync,
        isPending: mutation.isPending,
    };
}

