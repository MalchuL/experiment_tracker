import { parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import { SCALARS_DEFAULT_SELECTED_EXPERIMENT_COUNT } from "@/domain/scalars/constants";

/** Newest-first experiment ids for the scalars page default selection (UI only). */
export function getDefaultSelectedExperimentIds(
  experiments: Experiment[],
  limit = SCALARS_DEFAULT_SELECTED_EXPERIMENT_COUNT
): string[] {
  return [...experiments]
    .sort((a, b) => parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime())
    .slice(0, Math.max(0, limit))
    .map((experiment) => experiment.id);
}
