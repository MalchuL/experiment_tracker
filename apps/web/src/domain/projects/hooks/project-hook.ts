import { useMutation, useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { projectsService } from "../services";
import { Project, UpdateProject } from "../types";
import { useCallback } from "react";


export interface ProjectHookOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface ProjectHookResult {
    project: Project;
    isLoading: boolean;
    updateIsPending: boolean;
    deleteIsPending: boolean;
    updateProject: (project: UpdateProject, options?: ProjectHookOptions) => Promise<void>;
    deleteProject: (options?: ProjectHookOptions) => Promise<void>;
}

export function useProject(projectId: string): ProjectHookResult {
    const { data: project, isLoading } = useQuery({
        queryKey: [QUERY_KEYS.PROJECTS.GET_BY_ID(projectId)],
        queryFn: () => projectsService.getById(projectId),
    }) as { data: Project, isLoading: boolean };


    const updateProject = useMutation({
        mutationFn: (project: UpdateProject) => projectsService.update(projectId, project) as unknown as Promise<void>,
    });

    const deleteProject = useMutation({
        mutationFn: () => projectsService.delete(projectId) as unknown as Promise<void>,
    });


    const deleteFn = useCallback((options?: ProjectHookOptions) => deleteProject.mutateAsync(undefined, options), [deleteProject]);
    return {
        project, isLoading,
        updateIsPending: updateProject.isPending,
        deleteIsPending: deleteProject.isPending,
        updateProject: updateProject.mutateAsync,
        deleteProject: deleteFn,
    };
}