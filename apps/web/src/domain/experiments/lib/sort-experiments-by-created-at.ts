import type { Experiment } from "../types";

/** Newest first; stable tie-break on id. */
export function compareExperimentsByCreatedAtDesc(a: Experiment, b: Experiment): number {
  const ta = Date.parse(a.createdAt);
  const tb = Date.parse(b.createdAt);
  if (Number.isFinite(tb) && Number.isFinite(ta) && tb !== ta) {
    return tb - ta;
  }
  return b.id.localeCompare(a.id);
}
