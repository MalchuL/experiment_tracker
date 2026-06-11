import { useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { Experiment } from "../types";
import { useEffect, useMemo } from "react";
import { compareExperimentsByCreatedAtDesc } from "../lib/sort-experiments-by-created-at";

/** Flattened infinite-query result plus helpers for project experiment lists (table, kanban, DAG, scalars sidebar). */
export interface UseExperimentsResult {
    experiments: Experiment[];
    /** Total rows matching the current query (same on every page); from the list API `total` field. */
    total: number;
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
    /**
     * Server-side filter on GET /projects/:id/experiments: case-insensitive substring on id, name,
     * and description. Pagination applies to matching rows project-wide (not only the client cache).
     */
    search?: string;
    /** Include feature trees in list items. Defaults false because features can be large. */
    includeFeatures?: boolean;
}

/**
 * Infinite list of experiments for a project, sorted newest-first. ``paginationMode`` controls whether
 * remaining pages auto-fetch (default) or wait for explicit scroll/load-more (experiments table).
 * Optional ``refetchInterval`` powers live lists (see ``live-refresh`` / ``rates`` constants).
 */
export function useExperiments(
    projectId?: string,
    options?: UseExperimentsQueryOptions
): UseExperimentsResult {
    const paginationMode = options?.paginationMode ?? "auto";
    const searchParam =
        options?.search !== undefined && options.search.trim() !== ""
            ? options.search.trim()
            : undefined;
    const includeFeatures = options?.includeFeatures ?? false;

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
            ? [
                  QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId),
                  { limit: DEFAULT_PAGE_SIZE, mode: paginationMode, search: searchParam, includeFeatures },
              ]
            : [],
        queryFn: ({ pageParam }) =>
            experimentsService.getByProject(projectId!, {
                limit: DEFAULT_PAGE_SIZE,
                offset: pageParam,
                ...(searchParam ? { search: searchParam } : {}),
                includeFeatures,
            }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, allPages) => {
            if (!lastPage.hasNext) {
                return undefined;
            }
            return allPages.reduce((total, page) => total + page.data.length, 0);
        },
        enabled: !!projectId && (options?.enabled ?? true),
        staleTime: 30000, // 30 seconds — refetchInterval still fires per TanStack Query rules
        refetchInterval: options?.refetchInterval,
        placeholderData: keepPreviousData,
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

    const total = data?.pages[0]?.total ?? 0;

    return {
        experiments,
        total,
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

