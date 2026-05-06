import { useInfiniteQuery } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { Experiment } from "../types";
import { useEffect, useMemo } from "react";
import { compareExperimentsByCreatedAtDesc } from "../lib/sort-experiments-by-created-at";

export interface UseExperimentsResult {
    experiments: Experiment[];
    isLoading: boolean;
    isFetching: boolean;
    isFetchingNextPage: boolean;
    hasNextPage: boolean;
    fetchNextPage: () => Promise<unknown>;
    refetch: () => Promise<unknown>;
}

export interface UseExperimentsQueryOptions {
    refetchInterval?: number | false;
    paginationMode?: "auto" | "scroll";
    /** When false, the query does not run (e.g. open a menu first). Default true. */
    enabled?: boolean;
}

export function useExperiments(
    projectId?: string,
    options?: UseExperimentsQueryOptions
): UseExperimentsResult {
    const paginationMode = options?.paginationMode ?? "auto";
    const {
        data,
        isLoading,
        isFetching,
        isFetchingNextPage,
        hasNextPage,
        fetchNextPage,
        refetch,
    } = useInfiniteQuery({
        queryKey: projectId
            ? [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId), { limit: DEFAULT_PAGE_SIZE, mode: paginationMode }]
            : [],
        queryFn: ({ pageParam }) =>
            experimentsService.getByProject(projectId!, {
                limit: DEFAULT_PAGE_SIZE,
                offset: pageParam,
            }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, allPages) => {
            if (!lastPage.hasNext) {
                return undefined;
            }
            return allPages.reduce((total, page) => total + page.data.length, 0);
        },
        enabled: !!projectId && (options?.enabled ?? true),
        staleTime: 30000, // 30 seconds
        refetchInterval: options?.refetchInterval,
    });
    useEffect(() => {
        if (paginationMode === "auto" && hasNextPage && !isFetchingNextPage) {
            void fetchNextPage();
        }
    }, [
        data?.pages.length,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
        paginationMode,
    ]);

    const experiments = useMemo(() => {
        const flat = data?.pages.flatMap((page) => page.data) ?? [];
        return [...flat].sort(compareExperimentsByCreatedAtDesc);
    }, [data]);

    return {
        experiments,
        isLoading,
        isFetching,
        isFetchingNextPage,
        hasNextPage: Boolean(hasNextPage),
        fetchNextPage: async () => {
            await fetchNextPage();
        },
        refetch,
    };
}


