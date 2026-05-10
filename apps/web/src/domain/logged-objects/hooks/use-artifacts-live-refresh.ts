import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "@/domain/scalars/services";

interface UseArtifactsLiveRefreshParams {
  projectId?: string;
  experimentIds: string[];
  artifactsQueryKey: readonly unknown[];
  enabled?: boolean;
}

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
