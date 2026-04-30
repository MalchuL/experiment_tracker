/**
 * Persists the experiments table **manual order** (`order` column) via the reorder API.
 *
 * The list UI sorts rows by **`createdAt` (newest first)**; dragging does not reshuffle the cache.
 * On optimistic update we only patch each row’s numeric **`order`** to match the new sequence until
 * `invalidateQueries` refetches.
 */
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
    /** Sends `orderedExperimentIds` to the backend reorder endpoint. */
    reorderExperiments: (
        orderedExperimentIds: string[],
        options?: UseReorderExperimentsOptions
    ) => Promise<Experiment[]>;
    isPending: boolean;
}

/**
 * Updates `experiment.order` to each id’s index in `orderedExperimentIds` across all cached pages.
 * Does not change array order or pagination—only the `order` field on matching rows.
 */
function applyManualOrderToExperimentPagesCache(
    current: InfiniteData<PaginatedResponse<Experiment>> | undefined,
    orderedExperimentIds: string[]
): InfiniteData<PaginatedResponse<Experiment>> | undefined {
    if (!current) {
        return current;
    }
    const orderIndexById = new Map(orderedExperimentIds.map((id, i) => [id, i]));
    return {
        ...current,
        pages: current.pages.map((page) => ({
            ...page,
            data: page.data.map((e) => {
                const nextOrder = orderIndexById.get(e.id);
                return nextOrder !== undefined ? { ...e, order: nextOrder } : e;
            }),
        })),
    };
}

/** Mutation hook for `POST …/experiments/reorder` (manual `order` only; list sort stays by `createdAt`). */
export function useReorderExperiments(projectId?: string): UseReorderExperimentsResult {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    const mutation = useMutation({
        mutationFn: async (orderedExperimentIds: string[]) => {
            if (!projectId) throw new Error("Project ID is required");
            return experimentsService.reorder(projectId, orderedExperimentIds);
        },
        onMutate: async (orderedExperimentIds: string[]) => {
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
                    applyManualOrderToExperimentPagesCache(data, orderedExperimentIds)
                );
            });

            return { previousExperiments };
        },
        onError: (_err, _orderedExperimentIds, context) => {
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
