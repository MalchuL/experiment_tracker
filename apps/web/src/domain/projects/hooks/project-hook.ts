import { useMutation, useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import type { CategoryCleanupResponse } from "@/domain/experiments/types";
import { projectsService } from "../services";
import type { Project, UpdateProject } from "../types";
import { useCallback } from "react";

export interface ProjectHookOptions {
  onSuccess?: () => void;
  onDeleteSuccess?: (result: CategoryCleanupResponse) => void;
  onError?: (error: Error) => void;
}

export interface ProjectHookResult {
  project: Project | undefined;
  isLoading: boolean;
  updateIsPending: boolean;
  deleteIsPending: boolean;
  updateProject: (project: UpdateProject, options?: ProjectHookOptions) => Promise<void>;
  deleteProject: (options?: ProjectHookOptions) => Promise<void>;
}

export function useProject(projectId?: string): ProjectHookResult {
  const { data: project, isLoading } = useQuery({
    queryKey: projectId ? [QUERY_KEYS.PROJECTS.GET_BY_ID(projectId)] : [],
    queryFn: () => projectsService.getById(projectId!),
    enabled: !!projectId,
  });

  const updateProject = useMutation({
    mutationFn: (project: UpdateProject) =>
      projectsService.update(projectId!, project) as unknown as Promise<void>,
  });

  const deleteProjectMutation = useMutation({
    mutationFn: () => projectsService.delete(projectId!),
  });

  const deleteFn = useCallback(
    (options?: ProjectHookOptions) =>
      deleteProjectMutation
        .mutateAsync(undefined, {
          onSuccess: (result) => {
            options?.onDeleteSuccess?.(result);
            options?.onSuccess?.();
          },
          onError: options?.onError,
        })
        .then(() => undefined),
    [deleteProjectMutation],
  );

  return {
    project,
    isLoading,
    updateIsPending: updateProject.isPending,
    deleteIsPending: deleteProjectMutation.isPending,
    updateProject: updateProject.mutateAsync,
    deleteProject: deleteFn,
  };
}
