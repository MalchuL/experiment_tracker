import { useEffect, useRef } from "react";
import { InfiniteData, useQuery, useQueryClient } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "@/domain/scalars/services";
import type { ScalarsPointsResult } from "@/domain/scalars/types";
import { mergeScalarsPage } from "@/domain/scalars/utils";

interface UseScalarsLiveRefreshParams {
  projectId?: string;
  experimentIds: string[];
  scalarsQueryKey: readonly unknown[];
  maxPoints: number;
  enabled?: boolean;
}

/**
 * Incremental live refresh for **project scalar curves**: polls ``GET .../last_logged/{project}`` for the
 * watched experiments; when any ``last_modified`` moves forward, fetches only rows after the previous
 * watermark (``startTime`` + affected ids) and **merges** into the existing infinite-query cache via
 * ``mergeScalarsPage`` — avoids full refetch of all pages.
 *
 * Uses the same ``last_logged`` query key as ``useArtifactsLiveRefresh`` when both are enabled so only
 * one poll runs per interval.
 */
export function useScalarsLiveRefresh({
  projectId,
  experimentIds,
  scalarsQueryKey,
  maxPoints,
  enabled = true,
}: UseScalarsLiveRefreshParams) {
  const queryClient = useQueryClient();
  const previousByExperiment = useRef<Map<string, string>>(new Map());
  const stableExperimentIds = [...experimentIds].sort();

  const { data } = useQuery({
    queryKey: projectId
      ? [
          QUERY_KEYS.SCALARS.LAST_LOGGED(projectId),
          { experimentIds: stableExperimentIds },
        ]
      : [],
    queryFn: () => scalarsService.getLastLoggedByProject(projectId!, stableExperimentIds),
    enabled: !!projectId && enabled && stableExperimentIds.length > 0,
    refetchInterval: LAST_LOGGED_POLL_INTERVAL_MS,
  });

  /**
   * Diff ``last_logged`` against ref; skip first poll (no prior timestamps). Fetch incremental scalar
   * slice and merge each infinite page in-place with ``setQueryData``.
   */
  useEffect(() => {
    if (!projectId || !data?.data.length) return;

    const previous = previousByExperiment.current;
    const changed = data.data
      .map((item) => ({ item, previousModified: previous.get(item.experiment_id) }))
      .filter(({ item, previousModified }) => {
        if (!previousModified) return false;
        return new Date(item.last_modified).getTime() > new Date(previousModified).getTime();
      });

    data.data.forEach((item) => {
      previous.set(item.experiment_id, item.last_modified);
    });

    if (changed.length === 0) return;

    void (async () => {
      const startTime = changed
        .map(({ previousModified }) => previousModified)
        .filter((value): value is string => !!value)
        .sort()[0];
      const latest = await scalarsService.getByProject(projectId, {
        experimentIds: changed.map(({ item }) => item.experiment_id),
        maxPoints,
        returnTags: false,
        startTime,
        limit: Math.max(changed.length, 1),
      });
      queryClient.setQueryData<InfiniteData<ScalarsPointsResult>>(scalarsQueryKey, (current) => {
        if (!current) return current;
        return {
          ...current,
          pages: current.pages.map((page) => mergeScalarsPage(page, latest.data)),
        };
      });
    })();
  }, [data, maxPoints, projectId, queryClient, scalarsQueryKey]);
}
