import { useQueries, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "../services";
import { refreshScalarCache, type ScalarCache } from "../utils/refresh-scalar-cache";
import type { ExperimentScalarsPoints } from "../types";

export type IncrementalScalarsRefreshResult = "updated" | "unchanged" | "unavailable";

/** Only mounted plots subscribe. Query data owns both sampled history and its watermark. */
export function useScalarsLiveRefresh({ projectId, experimentIds, scalarNames, maxPoints, enabled = true }: {
  projectId?: string;
  experimentIds: string[];
  scalarNames: string[];
  maxPoints: number;
  enabled?: boolean;
}) {
  const client = useQueryClient();
  const ids = [...experimentIds].sort();
  const names = [...new Set(scalarNames)].sort();
  const result = useQueries({ combine: combineScalarQueries, queries: names.map((name) => {
    const queryKey = [QUERY_KEYS.SCALARS.BY_PROJECT(projectId ?? ""), "sampled-scalar", { experimentIds: ids, name, maxPoints }];
    return {
      queryKey,
      enabled: !!projectId && ids.length > 0,
      staleTime: 0,
      refetchOnMount: "always" as const,
      refetchInterval: enabled ? LAST_LOGGED_POLL_INTERVAL_MS : false as const,
      queryFn: async ({ signal }: { signal: AbortSignal }) => {
        // Simultaneous card requests share this lightweight poll, not their watermarks.
        const latest = await client.fetchQuery({
          queryKey: [QUERY_KEYS.SCALARS.LAST_LOGGED(projectId!), { experimentIds: ids }],
          queryFn: () => scalarsService.getLastLoggedByProject(projectId!, ids),
          staleTime: 0,
        });
        signal.throwIfAborted();
        return refreshScalarCache(client.getQueryData<ScalarCache>(queryKey), latest.data,
          async (changedIds, startTime) => {
            const result = await scalarsService.getAllByProject(projectId!, {
              experimentIds: changedIds ?? ids, scalarNames: [name], maxPoints,
              returnTags: false, storeCache: false, startTime, signal,
            });
            signal.throwIfAborted();
            return result.data;
          }, maxPoints);
      },
    };
  }) });
  return {
    scalars: result.scalars,
    isFetching: result.isFetching,
    statusByMetric: Object.fromEntries(names.map((name, index) => [name, {
      loading: ids.length > 0 && result.statuses[index].loading,
      error: result.statuses[index].error,
    }])),
    lastPollAt: result.lastPollAt,
    refreshChangedScalars: async (): Promise<IncrementalScalarsRefreshResult> => {
      if (ids.length > 0) await Promise.all(result.refetches.map((refetch) => refetch({ cancelRefetch: false })));
      return "updated";
    },
  };
}

// TanStack structurally shares the combined result, including unchanged scalar arrays.
function combineScalarQueries(queries: UseQueryResult<ScalarCache>[]) {
  const byId = new Map<string, ExperimentScalarsPoints>();
  for (const query of queries) for (const entry of query.data?.data ?? []) {
    const previous = byId.get(entry.experiment_id);
    byId.set(entry.experiment_id, { ...entry, scalars: { ...previous?.scalars, ...entry.scalars } });
  }
  return {
    scalars: [...byId.values()],
    isFetching: queries.some((query) => query.isFetching),
    statuses: queries.map((query) => ({ loading: query.isPending, error: query.isError })),
    lastPollAt: Math.max(0, ...queries.map((query) => query.dataUpdatedAt)),
    refetches: queries.map((query) => query.refetch),
  };
}
