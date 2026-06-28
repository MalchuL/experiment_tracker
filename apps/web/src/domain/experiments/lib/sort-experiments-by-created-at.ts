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

/** Oldest first; stable tie-break on id. */
export function compareExperimentsByCreatedAtAsc(a: Experiment, b: Experiment): number {
  const ta = Date.parse(a.createdAt);
  const tb = Date.parse(b.createdAt);
  if (Number.isFinite(ta) && Number.isFinite(tb) && ta !== tb) {
    return ta - tb;
  }
  return a.id.localeCompare(b.id);
}
