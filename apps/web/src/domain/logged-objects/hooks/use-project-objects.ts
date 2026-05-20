import { useInfiniteQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { loggedObjectsService } from "../services";
import { useEffect, useMemo } from "react";

/** Filters for listing logged-at-step artifacts (artifacts_info) for ``useProjectObjects``. */
export interface UseProjectObjectsParams {
  projectId?: string;
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  maxSteps?: number;
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
  const hasExplicitEmptyExperimentSelection = experimentIds !== undefined && experimentIds.length === 0;
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
    enabled: !!projectId && !hasExplicitEmptyExperimentSelection,
  });
  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [data?.pages.length, fetchNextPage, hasNextPage, isFetchingNextPage]);

  const artifacts = useMemo(
    () => {
      if (hasExplicitEmptyExperimentSelection) return [];
      return data?.pages.flatMap((page) => page.data) ?? [];
    },
    [data, hasExplicitEmptyExperimentSelection]
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

/**
 * Infinite query over lightweight artifact summaries for the scalars page object sliders.
 *
 * Unlike ``useProjectObjects``, this does not load object paths/metadata. It fetches only
 * ``name + artifact_type + sampled steps + last_modified`` per experiment. Visible cards download
 * directly by experiment/name/type/step and use ``last_modified`` to cache-bust media URLs.
 */
export function useProjectObjectSummaries(params: UseProjectObjectsParams) {
  const { projectId, experimentIds, objectTypes, names, maxSteps, startTime, endTime } = params;
  const stableExperimentIds = [...(experimentIds ?? [])].sort();
  const stableObjectTypes = [...(objectTypes ?? [])].sort();
  const stableNames = [...(names ?? [])].sort();
  const hasExplicitEmptyExperimentSelection = experimentIds !== undefined && experimentIds.length === 0;
  const queryKey = projectId
    ? [
        QUERY_KEYS.ARTIFACTS.BY_PROJECT(projectId),
        "summary",
        {
          experimentIds: stableExperimentIds,
          limit: DEFAULT_PAGE_SIZE,
          objectTypes: stableObjectTypes,
          names: stableNames,
          maxSteps,
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
      loggedObjectsService.getSummaryByProject(projectId!, {
        experimentIds: stableExperimentIds,
        limit: DEFAULT_PAGE_SIZE,
        offset: pageParam,
        objectTypes: stableObjectTypes,
        names: stableNames,
        maxSteps,
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

  const artifacts = useMemo(
    () => {
      if (hasExplicitEmptyExperimentSelection) return [];
      return data?.pages.flatMap((page) => page.data) ?? [];
    },
    [data, hasExplicitEmptyExperimentSelection]
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
