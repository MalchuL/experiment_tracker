import { useInfiniteQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { scalarsService } from "../services";
import type { ScalarsPointsResult } from "../types";
import { useEffect, useMemo } from "react";

/** Request filters for ``useProjectScalars`` (optional experiment subset, sampling, time bounds). */
export interface UseProjectScalarsParams {
  projectId?: string;
  experimentIds?: string[];
  maxPoints?: number;
  returnTags?: boolean;
  startTime?: string;
  endTime?: string;
}

/** Flattened per-experiment scalar series plus the infinite-query ``queryKey`` for cache merges (live refresh). */
export interface UseProjectScalarsResult {
  scalars: ScalarsPointsResult["data"];
  queryKey: readonly unknown[];
  isLoading: boolean;
  isFetching: boolean;
  isFetchingNextPage: boolean;
  refetch: () => Promise<unknown>;
}

/**
 * Infinite query over **project scalar curves** from the main API (→ scalars satellite). Concatenates pages
 * into ``scalars``; auto-fetches remaining pages like ``useProjectObjects``.
 *
 * ``queryKey`` must stay aligned with ``useScalarsLiveRefresh`` when patching cache after ``last_logged``.
 */
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
  const hasExplicitEmptyExperimentSelection = experimentIds !== undefined && experimentIds.length === 0;
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
    enabled: !!projectId && !hasExplicitEmptyExperimentSelection,
  });
  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [data?.pages.length, fetchNextPage, hasNextPage, isFetchingNextPage]);

  const scalars = useMemo(
    () => {
      if (hasExplicitEmptyExperimentSelection) return [];
      return data?.pages.flatMap((page) => page.data) ?? [];
    },
    [data, hasExplicitEmptyExperimentSelection]
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
