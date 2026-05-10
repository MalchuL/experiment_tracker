import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "@/domain/scalars/services";

/** Mirrors ``useScalarsLiveRefresh`` inputs but targets the artifacts infinite query key instead of merging scalars. */
interface UseArtifactsLiveRefreshParams {
  projectId?: string;
  /** Same ids passed to ``useScalarsLiveRefresh`` so both hooks share one ``last_logged`` React Query subscription. */
  experimentIds: string[];
  artifactsQueryKey: readonly unknown[];
  enabled?: boolean;
}

/**
 * Live refresh for **logged objects at step** (artifacts_info): polls ``last_logged`` per experiment,
 * and when ``last_modified`` advances invalidates the project artifacts infinite query so images/lists refetch.
 *
 * Shares the **same query key** as ``useScalarsLiveRefresh`` for ``last_logged``, so TanStack Query
 * performs a single network poll when both hooks are mounted.
 */
export function useArtifactsLiveRefresh({
  projectId,
  experimentIds,
  artifactsQueryKey,
  enabled = true,
}: UseArtifactsLiveRefreshParams) {
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
   * Compare successive ``last_logged`` payloads; first poll only seeds ``previousByExperiment``.
   * On change, invalidate artifacts cache so React Query refetches all loaded pages.
   */
  useEffect(() => {
    if (!projectId || !data?.data.length || !artifactsQueryKey.length) return;

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

    void queryClient.invalidateQueries({ queryKey: artifactsQueryKey });
  }, [artifactsQueryKey, data, projectId, queryClient]);
}
