import type {
  ArtifactsInfoSummaryResult,
  ExperimentArtifactsSummary,
  LoggedArtifactSummaryEntry,
} from "@/domain/logged-objects/types";

export function mergeExperimentArtifactsSummary(
  current: ExperimentArtifactsSummary,
  incoming: ExperimentArtifactsSummary
): ExperimentArtifactsSummary {
  /** Merge cached and incoming summary rows by artifact type/name, unioning sampled steps. */
  const byKey = new Map<string, LoggedArtifactSummaryEntry>();

  current.artifacts_info.forEach((item) => {
    byKey.set(summaryEntryKey(item), item);
  });
  incoming.artifacts_info.forEach((item) => {
    const key = summaryEntryKey(item);
    const existing = byKey.get(key);
    byKey.set(key, existing ? mergeSummaryEntry(existing, item) : item);
  });

  return {
    ...current,
    artifacts_info: Array.from(byKey.values()).sort(compareSummaryEntries),
  };
}

export function mergeArtifactsInfoPage(
  page: ArtifactsInfoSummaryResult,
  incoming: ExperimentArtifactsSummary[],
  options: { appendMissing?: boolean } = {}
): ArtifactsInfoSummaryResult {
  /** Patch one infinite-query summary page during manual/timed artifact refresh. */
  const incomingByExperiment = new Map(incoming.map((item) => [item.experiment_id, item]));
  const currentExperimentIds = new Set(page.data.map((item) => item.experiment_id));
  const missingIncoming = options.appendMissing
    ? incoming.filter((item) => !currentExperimentIds.has(item.experiment_id))
    : [];

  return {
    ...page,
    data: [
      ...missingIncoming.map(sortExperimentArtifactsSummary),
      ...page.data.map((current) => {
        const next = incomingByExperiment.get(current.experiment_id);
        return next ? mergeExperimentArtifactsSummary(current, next) : current;
      }),
    ],
  };
}

function mergeSummaryEntry(
  current: LoggedArtifactSummaryEntry,
  incoming: LoggedArtifactSummaryEntry
): LoggedArtifactSummaryEntry {
  return {
    ...current,
    steps: Array.from(new Set([...current.steps, ...incoming.steps])).sort((a, b) => a - b),
    last_modified:
      new Date(incoming.last_modified).getTime() > new Date(current.last_modified).getTime()
        ? incoming.last_modified
        : current.last_modified,
  };
}

function sortExperimentArtifactsSummary(
  item: ExperimentArtifactsSummary
): ExperimentArtifactsSummary {
  return {
    ...item,
    artifacts_info: [...item.artifacts_info].sort(compareSummaryEntries),
  };
}

function summaryEntryKey(item: LoggedArtifactSummaryEntry): string {
  return `${item.artifact_type}\u0000${item.name}`;
}

function compareSummaryEntries(a: LoggedArtifactSummaryEntry, b: LoggedArtifactSummaryEntry): number {
  const typeCompare = a.artifact_type.localeCompare(b.artifact_type);
  if (typeCompare !== 0) return typeCompare;

  return a.name.localeCompare(b.name);
}
