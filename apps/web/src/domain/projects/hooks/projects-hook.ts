import { toast } from "@/lib/hooks/use-toast";
import { projectsService } from "../services/projects-service";
import { Project, InsertProject } from "../types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ProjectHookOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface ProjectsHookResult {
    projects: Project[];
    isLoading: boolean;
    creationIsPending: boolean;
    deletionIsPending: boolean;
    createProject: (data: InsertProject, options?: ProjectHookOptions) => Promise<void>;
    deleteProject: (id: string, options?: ProjectHookOptions) => Promise<void>;
}

export function useProjects() {
    // List projects query
    const { data: projects, isLoading } = useQuery({
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
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DASHBOARD.STATS] });
        },
    });

    // Delete project mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            return projectsService.delete(id);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DASHBOARD.STATS] });
        }
    });

    return {
        projects,
        isLoading,
        creationIsPending: createMutation.isPending,
        deletionIsPending: deleteMutation.isPending,
        createProject: createMutation.mutateAsync,
        deleteProject: deleteMutation.mutateAsync
    };
}