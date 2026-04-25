import { InfiniteData, QueryKey, useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { Experiment } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import type { PaginatedResponse } from "@/lib/types/pagination";

export interface UseReorderExperimentsOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseReorderExperimentsResult {
    reorderExperiments: (experimentIds: string[], options?: UseReorderExperimentsOptions) => Promise<Experiment[]>;
    isPending: boolean;
}

function reorderExperimentPages(
    current: InfiniteData<PaginatedResponse<Experiment>> | undefined,
    experimentIds: string[]
): InfiniteData<PaginatedResponse<Experiment>> | undefined {
    if (!current) {
        return current;
    }

    const experiments = current.pages.flatMap((page) => page.data);
    const reorderedExperiments = experimentIds
        .map((id, index) => {
            const experiment = experiments.find((candidate) => candidate.id === id);
            return experiment ? { ...experiment, order: index } : null;
        })
        .filter((experiment): experiment is Experiment => experiment !== null);

    let cursor = 0;

    return {
        ...current,
        pages: current.pages.map((page) => {
            const nextPageData = reorderedExperiments.slice(
                cursor,
                cursor + page.data.length
            );
            cursor += page.data.length;

            return {
                ...page,
                data: nextPageData,
                size: nextPageData.length,
            };
        }),
    };
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
            if (!projectId) {
                return {
                    previousExperiments: [] as Array<
                        [
                            QueryKey,
                            InfiniteData<PaginatedResponse<Experiment>> | undefined
                        ]
                    >,
                };
            }

            await queryClient.cancelQueries({
                queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
            });

            const previousExperiments = queryClient.getQueriesData<
                InfiniteData<PaginatedResponse<Experiment>>
            >({
                queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
            });

            previousExperiments.forEach(([queryKey, data]) => {
                queryClient.setQueryData(
                    queryKey,
                    reorderExperimentPages(data, experimentIds)
                );
            });

            return { previousExperiments };
        },
        onError: (_err, _experimentIds, context) => {
            context?.previousExperiments?.forEach(([queryKey, data]) => {
                queryClient.setQueryData(queryKey, data);
            });
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

