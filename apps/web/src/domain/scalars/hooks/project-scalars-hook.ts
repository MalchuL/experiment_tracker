import { useInfiniteQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { scalarsService } from "../services";
import type { ScalarsPointsResult } from "../types";
import { useEffect, useMemo } from "react";

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
  queryKey: readonly unknown[];
  isLoading: boolean;
  isFetching: boolean;
  isFetchingNextPage: boolean;
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
          limit: DEFAULT_PAGE_SIZE,
          maxPoints,
          returnTags,
          startTime,
          endTime,
        },
      ]
    : [];

  const {
    data,
    isLoading,
    isFetching,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch,
  } = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) =>
      scalarsService.getByProject(projectId!, {
        experimentIds: stableExperimentIds,
        limit: DEFAULT_PAGE_SIZE,
        offset: pageParam,
        maxPoints,
        returnTags,
        startTime,
        endTime,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.hasNext) {
        return undefined;
      }
      return allPages.reduce((total, page) => total + page.data.length, 0);
    },
    enabled: !!projectId,
  });
  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [data?.pages.length, fetchNextPage, hasNextPage, isFetchingNextPage]);

  const scalars = useMemo(
    () => data?.pages.flatMap((page) => page.data) ?? [],
    [data]
  );

  return {
    scalars,
    queryKey,
    isLoading,
    isFetching,
    isFetchingNextPage,
    refetch,
  };
}
