import { projectsService } from "../services";
import { Project, InsertProject } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";

export interface ProjectsHookOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface ProjectsHookResult {
    projects: Project[];
    isLoading: boolean;
    isFetching: boolean;
    isFetchingNextPage: boolean;
    creationIsPending: boolean;
    deletionIsPending: boolean;
    createProject: (data: InsertProject, options?: ProjectsHookOptions) => Promise<void>;
    deleteProject: (id: string, options?: ProjectsHookOptions) => Promise<void>;
    error: Error | null;
}

export function useProjects() {
    const {
        data,
        isLoading,
        isFetching,
        isFetchingNextPage,
        hasNextPage,
        fetchNextPage,
        error,
    } = useInfiniteQuery({
        queryKey: [QUERY_KEYS.PROJECTS.LIST, { limit: DEFAULT_PAGE_SIZE }],
        queryFn: ({ pageParam }) =>
            projectsService.getAll({
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
    });
    useEffect(() => {
        if (hasNextPage && !isFetchingNextPage) {
            void fetchNextPage();
        }
    }, [fetchNextPage, hasNextPage, isFetchingNextPage, data?.pages.length]);

    const projects = useMemo(
        () => data?.pages.flatMap((page) => page.data) ?? [],
        [data]
    );
    const queryClient = useQueryClient();
    // Create project mutation
    const createMutation = useMutation({
        mutationFn: async (data: InsertProject) => {
            return projectsService.create(data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
        },
    });

    // Delete project mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            return projectsService.delete(id);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
        }
    });

    return {
        projects,
        isLoading,
        isFetching,
        isFetchingNextPage,
        creationIsPending: createMutation.isPending,
        deletionIsPending: deleteMutation.isPending,
        createProject: createMutation.mutateAsync,
        deleteProject: deleteMutation.mutateAsync,
        error: error as Error | null,
    };
}