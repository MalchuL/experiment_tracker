export function findMissingExperimentIds(params: {
  selectedExperimentIds: Set<string> | Iterable<string>;
  requestedExperimentIds: string[];
  fetchedExperimentIds: string[];
  incrementalInFlightIds: Set<string>;
}): string[] {
  const fetchedIds = new Set([
    ...params.requestedExperimentIds,
    ...params.fetchedExperimentIds,
  ]);

  return Array.from(params.selectedExperimentIds).filter(
    (id) => !fetchedIds.has(id) && !params.incrementalInFlightIds.has(id)
  );
}
