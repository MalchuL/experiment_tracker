import { projectsService } from "../services";
import { Project, InsertProject } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ProjectsHookOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface ProjectsHookResult {
    projects: Project[];
    isLoading: boolean;
    creationIsPending: boolean;
    deletionIsPending: boolean;
    createProject: (data: InsertProject, options?: ProjectsHookOptions) => Promise<void>;
    deleteProject: (id: string, options?: ProjectsHookOptions) => Promise<void>;
    error: Error | null;
}

export function useProjects() {
    // List projects query
    const { data: projects, isLoading, error } = useQuery({
        queryKey: [QUERY_KEYS.PROJECTS.LIST],
        queryFn: () => projectsService.getAll(),
    });
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
        creationIsPending: createMutation.isPending,
        deletionIsPending: deleteMutation.isPending,
        createProject: createMutation.mutateAsync,
        deleteProject: deleteMutation.mutateAsync,
        error
    };
}