import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { loggedObjectsService } from "../services";
import type { ProjectObjectsResult } from "../types";

export interface UseProjectObjectsParams {
  projectId?: string;
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  startTime?: string;
  endTime?: string;
}

export function useProjectObjects(params: UseProjectObjectsParams) {
  const { projectId, experimentIds, objectTypes, names, startTime, endTime } = params;
  const stableExperimentIds = [...(experimentIds ?? [])].sort();
  const stableObjectTypes = [...(objectTypes ?? [])].sort();
  const stableNames = [...(names ?? [])].sort();
  const queryKey = projectId
    ? [
        QUERY_KEYS.ARTIFACTS.BY_PROJECT(projectId),
        {
          experimentIds: stableExperimentIds,
          objectTypes: stableObjectTypes,
          names: stableNames,
          startTime,
          endTime,
        },
      ]
    : [];
  const { data, isLoading, isFetching, refetch } = useQuery<ProjectObjectsResult>({
    queryKey,
    queryFn: () =>
      loggedObjectsService.getByProject(projectId!, {
        experimentIds: stableExperimentIds,
        objectTypes: stableObjectTypes,
        names: stableNames,
        startTime,
        endTime,
      }),
    enabled: !!projectId,
  });
  return {
    objects: data?.data ?? [],
    isLoading,
    isFetching,
    refetch,
  };
}
