import { useInfiniteQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { loggedObjectsService } from "../services";
import type { ArtifactsInfoResult } from "../types";
import { useEffect, useMemo } from "react";

/** Filters for listing logged-at-step artifacts (artifacts_info) for ``useProjectObjects``. */
export interface UseProjectObjectsParams {
  projectId?: string;
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  startTime?: string;
  endTime?: string;
}

/**
 * Infinite query over project **artifacts at step** via the main API; concatenates pages so UI code sees
 * a flat ``artifacts`` list. An effect eagerly ``fetchNextPage``s until complete.
 *
 * Returns ``queryKey`` identical to the infinite query so ``useArtifactsLiveRefresh`` can invalidate or
 * patch the same cache entry.
 */
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
          limit: DEFAULT_PAGE_SIZE,
          objectTypes: stableObjectTypes,
          names: stableNames,
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
      loggedObjectsService.getByProject(projectId!, {
        experimentIds: stableExperimentIds,
        limit: DEFAULT_PAGE_SIZE,
        offset: pageParam,
        objectTypes: stableObjectTypes,
        names: stableNames,
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

  const artifacts = useMemo(
    () => data?.pages.flatMap((page) => page.data) ?? [],
    [data]
  );
  return {
    artifacts,
    queryKey,
    isLoading,
    isFetching,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch,
  };
}
