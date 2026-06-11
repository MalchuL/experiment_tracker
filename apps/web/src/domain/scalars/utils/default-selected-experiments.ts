import { parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import { SCALARS_DEFAULT_SELECTED_EXPERIMENT_COUNT } from "@/domain/scalars/constants";

function sortExperimentsNewestFirst(experiments: Experiment[]): Experiment[] {
  return [...experiments].sort(
    (a, b) => parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime()
  );
}

/** Newest-first experiment ids for the scalars page default selection (UI only). */
export function getDefaultSelectedExperimentIds(
  experiments: Experiment[],
  limit: number | null | undefined = SCALARS_DEFAULT_SELECTED_EXPERIMENT_COUNT
): string[] {
  const sorted = sortExperimentsNewestFirst(experiments);
  if (limit == null || limit === -1) {
    return sorted.map((experiment) => experiment.id);
  }
  return sorted.slice(0, Math.max(0, limit)).map((experiment) => experiment.id);
}
