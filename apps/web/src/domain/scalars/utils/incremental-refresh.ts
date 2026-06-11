export interface LastLoggedEntry {
  experiment_id: string;
  last_modified: string;
}

export interface IncrementalChangeEntry {
  item: LastLoggedEntry;
  previousModified: string | undefined;
  missingFromCache: boolean;
}

export function pickIncrementalChanges(params: {
  lastLogged: LastLoggedEntry[];
  cachedExperimentIds: Set<string>;
  previousModifiedByExperiment: Map<string, string>;
}): IncrementalChangeEntry[] {
  const { lastLogged, cachedExperimentIds, previousModifiedByExperiment } = params;

  return lastLogged
    .map((item) => ({
      item,
      previousModified: previousModifiedByExperiment.get(item.experiment_id),
      missingFromCache: !cachedExperimentIds.has(item.experiment_id),
    }))
    .filter(({ item, previousModified, missingFromCache }) => {
      if (missingFromCache) return true;
      if (!previousModified) return false;
      return new Date(item.last_modified).getTime() > new Date(previousModified).getTime();
    });
}

export function hasCompleteIncrementalBaseline(
  lastLogged: LastLoggedEntry[],
  previousModifiedByExperiment: Map<string, string>
): boolean {
  return lastLogged.every((item) => previousModifiedByExperiment.has(item.experiment_id));
}

export function computeIncrementalStartTime(
  changed: IncrementalChangeEntry[]
): string | undefined {
  const hasMissingCacheRows = changed.some(({ missingFromCache }) => missingFromCache);
  if (hasMissingCacheRows) {
    return undefined;
  }

  const timestamps = changed
    .map(({ previousModified }) => previousModified)
    .filter((value): value is string => !!value)
    .sort();

  return timestamps[0];
}
