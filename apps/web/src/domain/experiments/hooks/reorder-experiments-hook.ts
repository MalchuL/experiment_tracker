import { useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { Experiment } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export interface UseReorderExperimentsOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseReorderExperimentsResult {
    reorderExperiments: (experimentIds: string[], options?: UseReorderExperimentsOptions) => Promise<Experiment[]>;
    isPending: boolean;
}

export function useReorderExperiments(projectId?: string): UseReorderExperimentsResult {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    const mutation = useMutation({
        mutationFn: async (experimentIds: string[]) => {
            if (!projectId) throw new Error("Project ID is required");
            return experimentsService.reorder(projectId, experimentIds);
        },
        onMutate: async (experimentIds: string[]) => {
            if (!projectId) return { previousExperiments: undefined };

            await queryClient.cancelQueries({
                queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
            });

            const previousExperiments = queryClient.getQueryData<Experiment[]>(
                [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)]
            );

            queryClient.setQueryData<Experiment[]>(
                [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
                (old) => {
                    if (!old) return old;
                    return experimentIds.map((id, index) => {
                        const exp = old.find((e) => e.id === id);
                        return exp ? { ...exp, order: index } : null;
                    }).filter(Boolean) as Experiment[];
                }
            );

            return { previousExperiments };
        },
        onError: (_err, _experimentIds, context) => {
            if (context?.previousExperiments && projectId) {
                queryClient.setQueryData(
                    [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
                    context.previousExperiments
                );
            }
            toast({
                title: "Error",
                description: "Failed to reorder experiments.",
                variant: "destructive",
            });
        },
        onSettled: () => {
            if (projectId) {
                queryClient.invalidateQueries({
                    queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
                });
            }
        },
    });

    return {
        reorderExperiments: mutation.mutateAsync,
        isPending: mutation.isPending,
    };
}

