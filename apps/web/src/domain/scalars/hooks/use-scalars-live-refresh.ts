import { useCallback, useEffect, useMemo, useRef } from "react";
import { InfiniteData, useQuery, useQueryClient } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "@/domain/scalars/services";
import type { LastLoggedExperimentsResult, ScalarsPointsResult } from "@/domain/scalars/types";
import { mergeScalarsPage } from "@/domain/scalars/utils";
import {
  computeIncrementalStartTime,
  hasCompleteIncrementalBaseline,
  pickIncrementalChanges,
} from "@/domain/scalars/utils/incremental-refresh";

interface UseScalarsLiveRefreshParams {
  projectId?: string;
  experimentIds: string[];
  scalarsQueryKey: readonly unknown[];
  maxPoints: number;
  enabled?: boolean;
}

export type IncrementalScalarsRefreshResult = "updated" | "unchanged" | "unavailable";

/**
 * Incremental live refresh for **project scalar curves**: polls ``GET .../last_logged/{project}`` for the
 * watched experiments; when any ``last_modified`` moves forward, fetches only rows after the previous
 * watermark (``startTime`` + affected ids) and **merges** into the existing infinite-query cache via
 * ``mergeScalarsPage`` — avoids full refetch of all pages.
 *
 * Applies to both timed refresh (this hook's ``useEffect`` below) and manual refresh (the scalars
 * page button calls the returned ``refreshChangedScalars``). The merge re-samples each combined
 * metric series to ``maxPoints`` and always keeps the latest point.
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
  const stableExperimentIds = useMemo(() => [...experimentIds].sort(), [experimentIds]);

  const mergeChangedScalars = useCallback(
    async (lastLogged: LastLoggedExperimentsResult): Promise<IncrementalScalarsRefreshResult> => {
      if (!projectId || !lastLogged.data.length || !scalarsQueryKey.length) return "unavailable";

      const cached = queryClient.getQueryData<InfiniteData<ScalarsPointsResult>>(scalarsQueryKey);
      const cachedExperimentIds = new Set(
        cached?.pages.flatMap((page) => page.data.map((item) => item.experiment_id)) ?? []
      );
      const previous = previousByExperiment.current;
      const hasCompleteBaseline = hasCompleteIncrementalBaseline(lastLogged.data, previous);
      const changed = pickIncrementalChanges({
        lastLogged: lastLogged.data,
        cachedExperimentIds,
        previousModifiedByExperiment: previous,
      });

      lastLogged.data.forEach((item) => {
        previous.set(item.experiment_id, item.last_modified);
      });

      if (changed.length === 0) {
        return hasCompleteBaseline ? "unchanged" : "unavailable";
      }

      const startTime = computeIncrementalStartTime(changed);
      const latest = await scalarsService.getAllByProject(projectId, {
        experimentIds: changed.map(({ item }) => item.experiment_id),
        maxPoints,
        returnTags: false,
        ...(startTime ? { startTime } : {}),
      });
      queryClient.setQueryData<InfiniteData<ScalarsPointsResult>>(scalarsQueryKey, (current) => {
        if (!current) return current;
        return {
          ...current,
          pages: current.pages.map((page, index) =>
            // Same sampled merge path is used by timed polling and the manual refresh button.
            mergeScalarsPage(page, latest.data, { appendMissing: index === 0, maxPoints })
          ),
        };
      });
      return "updated";
    },
    [maxPoints, projectId, queryClient, scalarsQueryKey]
  );

  const refreshChangedScalars = useCallback(async (): Promise<IncrementalScalarsRefreshResult> => {
    if (!projectId || stableExperimentIds.length === 0) return "unavailable";
    const lastLogged = await scalarsService.getLastLoggedByProject(projectId, stableExperimentIds);
    return mergeChangedScalars(lastLogged);
  }, [mergeChangedScalars, projectId, stableExperimentIds]);

  const { data, dataUpdatedAt } = useQuery({
    queryKey: projectId
      ? [
          QUERY_KEYS.SCALARS.LAST_LOGGED(projectId),
          { experimentIds: stableExperimentIds },
        ]
      : [],
    queryFn: () => scalarsService.getLastLoggedByProject(projectId!, stableExperimentIds),
    enabled: !!projectId && enabled && stableExperimentIds.length > 0,
    refetchInterval: enabled ? LAST_LOGGED_POLL_INTERVAL_MS : false,
  });

  /**
   * Diff ``last_logged`` against ref; skip first poll (no prior timestamps). Fetch incremental scalar
   * slice and merge each infinite page in-place with ``setQueryData``.
   */
  useEffect(() => {
    if (!data) return;
    void mergeChangedScalars(data);
  }, [data, mergeChangedScalars]);

  return { refreshChangedScalars, lastPollAt: dataUpdatedAt };
}
