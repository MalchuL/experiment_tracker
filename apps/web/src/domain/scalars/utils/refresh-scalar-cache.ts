import type { ExperimentScalarsPoints } from "../types";
import type { LastLoggedEntry } from "./incremental-refresh";
import { mergeExperimentScalars } from "./merge-scalars";

export interface ScalarCache {
  data: ExperimentScalarsPoints[];
  watermarks: Record<string, string>;
}

/** Data and its server watermark are one transaction: a failed page commits neither. */
export async function refreshScalarCache(
  current: ScalarCache | undefined,
  latest: LastLoggedEntry[],
  fetchPoints: (experimentIds?: string[], startTime?: string) => Promise<ExperimentScalarsPoints[]>,
  maxPoints: number,
): Promise<ScalarCache> {
  const changed = latest.filter((entry) => !current?.watermarks[entry.experiment_id] ||
    Date.parse(entry.last_modified) > Date.parse(current.watermarks[entry.experiment_id]));
  if (current && changed.length === 0) return current;
  const previous = changed.map((entry) => current?.watermarks[entry.experiment_id]);
  const startTime = current && previous.length > 0 && previous.every(Boolean)
    ? (previous as string[]).sort((a, b) => Date.parse(a) - Date.parse(b))[0]
    : undefined;
  const incoming = await fetchPoints(current ? changed.map((entry) => entry.experiment_id) : undefined, startTime);
  const byId = new Map(current?.data.map((entry) => [entry.experiment_id, entry]));
  for (const entry of incoming) {
    byId.set(entry.experiment_id, mergeExperimentScalars(
      byId.get(entry.experiment_id) ?? { experiment_id: entry.experiment_id, scalars: {} },
      entry, { maxPoints },
    ));
  }
  return {
    data: [...byId.values()],
    watermarks: { ...current?.watermarks, ...Object.fromEntries(latest.map((entry) => [entry.experiment_id, entry.last_modified])) },
  };
}
