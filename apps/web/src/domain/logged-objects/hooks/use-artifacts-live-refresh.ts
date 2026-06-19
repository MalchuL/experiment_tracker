import { useCallback, useEffect, useMemo, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { InfiniteData } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "@/domain/scalars/services";
import type { LastLoggedExperimentsResult } from "@/domain/scalars/types";
import { loggedObjectsService } from "@/domain/logged-objects/services";
import type { ArtifactsInfoSummaryResult } from "@/domain/logged-objects/types";
import { mergeArtifactsInfoPage } from "@/domain/logged-objects/utils";
import {
  computeIncrementalStartTime,
  hasCompleteIncrementalBaseline,
  pickIncrementalChanges,
} from "@/domain/scalars/utils/incremental-refresh";

/** Mirrors ``useScalarsLiveRefresh`` inputs but targets the artifacts infinite query key and merge helper. */
interface UseArtifactsLiveRefreshParams {
  projectId?: string;
  /** Same ids passed to ``useScalarsLiveRefresh`` so both hooks share one ``last_logged`` React Query subscription. */
  experimentIds: string[];
  artifactsQueryKey: readonly unknown[];
  maxSteps: number;
  enabled?: boolean;
}

export type IncrementalArtifactsRefreshResult = "updated" | "unchanged" | "unavailable";

/**
 * Live refresh for **logged objects at step** (artifacts_info): polls ``last_logged`` per experiment,
 * and when ``last_modified`` advances fetches changed rows and merges them into the project artifacts cache.
 *
 * Shares the **same query key** as ``useScalarsLiveRefresh`` for ``last_logged``, so TanStack Query
 * performs a single network poll when both hooks are mounted.
 */
export function useArtifactsLiveRefresh({
  projectId,
  experimentIds,
  artifactsQueryKey,
  maxSteps,
  enabled = true,
}: UseArtifactsLiveRefreshParams) {
  const queryClient = useQueryClient();
  const previousByExperiment = useRef<Map<string, string>>(new Map());
  const stableExperimentIds = useMemo(() => [...experimentIds].sort(), [experimentIds]);

  const mergeChangedArtifacts = useCallback(
    async (lastLogged: LastLoggedExperimentsResult): Promise<IncrementalArtifactsRefreshResult> => {
      if (!projectId || !lastLogged.data.length || !artifactsQueryKey.length) return "unavailable";

      const cached = queryClient.getQueryData<InfiniteData<ArtifactsInfoSummaryResult>>(artifactsQueryKey);
      const cachedExperimentIds = new Set(
        cached?.pages.flatMap((page) => page.data.map((item) => item.experiment_id)) ?? []
      );
      const cachedModifiedByExperiment = getCachedModifiedByExperiment(cached);
      const previous = previousByExperiment.current;
      const previousModifiedByExperiment = new Map<string, string>();
      lastLogged.data.forEach((item) => {
        const baseline =
          previous.get(item.experiment_id) ?? cachedModifiedByExperiment.get(item.experiment_id);
        if (baseline) {
          previousModifiedByExperiment.set(item.experiment_id, baseline);
        }
      });

      const hasCompleteBaseline = hasCompleteIncrementalBaseline(
        lastLogged.data,
        previousModifiedByExperiment
      );
      const changed = pickIncrementalChanges({
        lastLogged: lastLogged.data,
        cachedExperimentIds,
        previousModifiedByExperiment,
      });

      lastLogged.data.forEach((item) => {
        previous.set(item.experiment_id, item.last_modified);
      });

      if (changed.length === 0) {
        return hasCompleteBaseline ? "unchanged" : "unavailable";
      }

      const startTime = computeIncrementalStartTime(changed);
      const changedWithBaseline = changed.filter(
        (entry): entry is typeof entry & { previousModified: string } =>
          !!entry.previousModified && !entry.missingFromCache
      );
      const changedWithoutBaseline = changed.filter(
        ({ previousModified, missingFromCache }) => !previousModified || missingFromCache
      );

      const [incrementalLatest, baselineLatest] = await Promise.all([
        changedWithBaseline.length
          ? loggedObjectsService.getAllSummaryByProject(projectId, {
              experimentIds: changedWithBaseline.map(({ item }) => item.experiment_id),
              maxSteps,
              startTime,
            })
          : undefined,
        changedWithoutBaseline.length
          ? loggedObjectsService.getAllSummaryByProject(projectId, {
              experimentIds: changedWithoutBaseline.map(({ item }) => item.experiment_id),
              maxSteps,
            })
          : undefined,
      ]);
      const latestData = [
        ...(incrementalLatest?.data ?? []),
        ...(baselineLatest?.data ?? []),
      ];

      queryClient.setQueryData<InfiniteData<ArtifactsInfoSummaryResult>>(artifactsQueryKey, (current) => {
        if (!current) return current;
        return {
          ...current,
          pages: current.pages.map((page, index) =>
            mergeArtifactsInfoPage(page, latestData, { appendMissing: index === 0 })
          ),
        };
      });
      return "updated";
    },
    [artifactsQueryKey, maxSteps, projectId, queryClient]
  );

  const refreshChangedArtifacts = useCallback(async (): Promise<IncrementalArtifactsRefreshResult> => {
    if (!projectId || stableExperimentIds.length === 0) return "unavailable";
    const lastLogged = await scalarsService.getLastLoggedByProject(projectId, stableExperimentIds);
    return mergeChangedArtifacts(lastLogged);
  }, [mergeChangedArtifacts, projectId, stableExperimentIds]);

  const { data } = useQuery({
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
   * Diff ``last_logged`` against ref; skip first poll (no prior timestamps). Fetch incremental
   * artifact rows and merge each infinite page in-place with ``setQueryData``.
   */
  useEffect(() => {
    if (!data) return;
    void mergeChangedArtifacts(data);
  }, [data, mergeChangedArtifacts]);

  return { refreshChangedArtifacts };
}

function getCachedModifiedByExperiment(
  cached: InfiniteData<ArtifactsInfoSummaryResult> | undefined
): Map<string, string> {
  const result = new Map<string, string>();
  cached?.pages.forEach((page) => {
    page.data.forEach((experimentArtifacts) => {
      experimentArtifacts.artifacts_info.forEach((item) => {
        const current = result.get(experimentArtifacts.experiment_id);
        if (!current || new Date(item.last_modified).getTime() > new Date(current).getTime()) {
          result.set(experimentArtifacts.experiment_id, item.last_modified);
        }
      });
    });
  });
  return result;
}
