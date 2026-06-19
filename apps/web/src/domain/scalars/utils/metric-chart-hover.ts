import type { ScalarHoverMode } from "@/domain/scalars/types";

export function truncateExperimentHoverName(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }
  if (maxLength <= 1) {
    return value.slice(0, maxLength);
  }
  return `${value.slice(0, maxLength - 1)}…`;
}

export function buildExperimentHoverDisplayNames(
  experiments: readonly { id: string; name: string }[],
  maxLength: number
): Map<string, string> {
  const result = new Map<string, string>();
  for (const experiment of experiments) {
    result.set(experiment.id, truncateExperimentHoverName(experiment.name, maxLength));
  }
  return result;
}

export function dedupeHoverRowsByExperimentAndStep<
  T extends { experimentId: string; step: number },
>(rows: T[]): T[] {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = `${row.experimentId}:${row.step}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function usesUnifiedMultiHover(mode: ScalarHoverMode): boolean {
  return mode === "compare" || mode === "visible";
}

export function isScalarYInVisibleRange(
  value: number,
  yRange: [number, number] | null | undefined
): boolean {
  if (yRange === null || yRange === undefined) {
    return true;
  }
  const [first, second] = yRange;
  const min = Math.min(first, second);
  const max = Math.max(first, second);
  return value >= min && value <= max;
}

export function filterHoverRowsToVisibleYRange<
  T extends { sortValue: number },
>(rows: T[], yRange: [number, number] | null | undefined): T[] {
  if (yRange === null || yRange === undefined) {
    return rows;
  }
  return rows.filter((row) => isScalarYInVisibleRange(row.sortValue, yRange));
}

export function resolveHoverYRangeFromEvent(
  points: ReadonlyArray<{ yaxis?: unknown }> | undefined,
  domainY: [number, number] | null | undefined
): [number, number] | null {
  const yaxis = points?.[0]?.yaxis as { range?: [number, number] } | undefined;
  if (Array.isArray(yaxis?.range) && yaxis.range.length === 2) {
    const [first, second] = yaxis.range;
    if (Number.isFinite(first) && Number.isFinite(second)) {
      return [first, second];
    }
  }
  return domainY ?? null;
}

const HOVER_MODE_CYCLE: ScalarHoverMode[] = ["compare", "visible", "nearest"];

export function getNextScalarHoverMode(mode: ScalarHoverMode): ScalarHoverMode {
  const index = HOVER_MODE_CYCLE.indexOf(mode);
  return HOVER_MODE_CYCLE[(index + 1) % HOVER_MODE_CYCLE.length]!;
}
