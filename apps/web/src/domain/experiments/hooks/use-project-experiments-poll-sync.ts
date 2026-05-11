/**
 * Bridges the **project experiments list** (React Query) with **heavy satellite caches** used on the
 * scalars page: project-wide scalar series and at-step artifact listings.
 *
 * Why it exists: polling or paging can surface new experiments or status transitions after the
 * scalars infinite queries already loaded. Without invalidation, charts and logged objects would
 * stay stale until a manual refresh.
 *
 * Algorithm: keep a map of ``experiment id → status``. On each ``experiments`` update, diff against
 * the previous snapshot; only when ids or statuses change do we invalidate scalars + artifacts by
 * partial query key (same keys as ``useProjectScalars`` / ``useProjectObjects``).
 */
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import type { Experiment, ExperimentStatusType } from "../types";

/**
 * Subscribes to ``experiments`` from ``useExperiments`` (typically with periodic refetch on the
 * scalars route). First non-empty list seeds the snapshot without invalidating; later drift triggers
 * invalidation so downstream queries refetch.
 */
export function useProjectExperimentsPollSync(
  projectId: string | undefined,
  experiments: Experiment[],
) {
  const queryClient = useQueryClient();
  const snapshotRef = useRef<Map<string, ExperimentStatusType>>(new Map());

  useEffect(() => {
    snapshotRef.current = new Map();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;

    const current = new Map<string, ExperimentStatusType>(
      experiments.map((e) => [e.id, e.status]),
    );
    const prev = snapshotRef.current;

    // Nothing loaded yet / still empty — nothing to compare.
    if (prev.size === 0 && current.size === 0) {
      return;
    }

    // Initial fill: remember baseline so the next diff does not treat “first paint” as drift.
    if (prev.size === 0 && current.size > 0) {
      snapshotRef.current = new Map(current);
      return;
    }

    let differs = false;

    // New id or status change on an id still present.
    for (const [id, status] of current) {
      if (!prev.has(id) || prev.get(id) !== status) {
        differs = true;
        break;
      }
    }

    // Removed experiment (deleted or no longer in page slice).
    if (!differs) {
      for (const id of prev.keys()) {
        if (!current.has(id)) {
          differs = true;
          break;
        }
      }
    }

    snapshotRef.current = new Map(current);

    if (!differs) {
      return;
    }

    void queryClient.invalidateQueries({
      queryKey: [QUERY_KEYS.SCALARS.BY_PROJECT(projectId)],
    });
    void queryClient.invalidateQueries({
      queryKey: [QUERY_KEYS.ARTIFACTS.BY_PROJECT(projectId)],
    });
  }, [experiments, projectId, queryClient]);
}
