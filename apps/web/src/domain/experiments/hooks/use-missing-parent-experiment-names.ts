import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { experimentsService } from "../services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import type { Experiment } from "../types";

const MAX_BATCH_IDS = 100;

/**
 * Fetches parent experiments by id when they are not in the current list (e.g. another page).
 * Uses POST …/experiments/batch — does not merge into the list; only for display (Parent column).
 */
export function useMissingParentExperimentNames(
  projectId: string | undefined,
  experiments: Experiment[]
) {
  const missingParentIds = useMemo(() => {
    const loadedIds = new Set(experiments.map((e) => e.id));
    const want = new Set<string>();
    for (const e of experiments) {
      const pid = e.parentExperimentId;
      if (pid && !loadedIds.has(pid)) want.add(pid);
    }
    return [...want].sort();
  }, [experiments]);

  const batchIds = useMemo(
    () => missingParentIds.slice(0, MAX_BATCH_IDS),
    [missingParentIds]
  );

  const batchKey = batchIds.join("|");

  const { data } = useQuery({
    queryKey: [
      QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId ?? ""),
      "batch-parent-names",
      batchKey,
    ],
    queryFn: () =>
      experimentsService.getByProjectBatch(projectId!, batchIds),
    enabled: Boolean(projectId && batchIds.length > 0),
    staleTime: 60_000,
  });

  return useMemo(() => {
    const map: Record<string, string> = {};
    for (const exp of data?.data ?? []) {
      map[exp.id] = exp.name;
    }
    return map;
  }, [data]);
}
