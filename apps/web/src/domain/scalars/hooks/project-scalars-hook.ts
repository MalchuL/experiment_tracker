import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "../services";
import type { ScalarsPointsResult } from "../types";

export interface UseProjectScalarsParams {
  projectId?: string;
  experimentIds?: string[];
  maxPoints?: number;
  returnTags?: boolean;
  startTime?: string;
  endTime?: string;
}

export interface UseProjectScalarsResult {
  scalars: ScalarsPointsResult["data"];
  isLoading: boolean;
  isFetching: boolean;
  refetch: () => Promise<unknown>;
}

export function useProjectScalars(
  params: UseProjectScalarsParams
): UseProjectScalarsResult {
  const {
    projectId,
    experimentIds,
    maxPoints,
    returnTags = false,
    startTime,
    endTime,
  } = params;

  const stableExperimentIds = [...(experimentIds ?? [])].sort();
  const queryKey = projectId
    ? [
        QUERY_KEYS.SCALARS.BY_PROJECT(projectId),
        {
          experimentIds: stableExperimentIds,
          maxPoints,
          returnTags,
          startTime,
          endTime,
        },
      ]
    : [];

  const { data, isLoading, isFetching, refetch } = useQuery<ScalarsPointsResult>({
    queryKey,
    queryFn: () =>
      scalarsService.getByProject(projectId!, {
        experimentIds: stableExperimentIds,
        maxPoints,
        returnTags,
        startTime,
        endTime,
      }),
    enabled: !!projectId,
  });

  return {
    scalars: data?.data ?? [],
    isLoading,
    isFetching,
    refetch,
  };
}
