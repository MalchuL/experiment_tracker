import type { ProjectDisplayMetric, ProjectMetric } from "@/domain/projects/types";

/**
 * Renders a metric for UI: unlabeled → name only; with label → `name:label`.
 */
export function formatMetricLabel(name: string, label: string | null | undefined): string {
  if (label == null || label === "") {
    return name;
  }
  return `${name}:${label}`;
}

export function displayMetricKeyEquals(
  a: { name: string; label?: string | null },
  b: { name: string; label?: string | null }
): boolean {
  return a.name === b.name && (a.label ?? null) === (b.label ?? null);
}

/** Legacy API may return display metrics as plain names. */
export function normalizeDisplayMetric(
  d: string | { name: string; label?: string | null }
): { name: string; label: string | null } {
  if (typeof d === "string") {
    return { name: d, label: null };
  }
  return { name: d.name, label: d.label ?? null };
}

export function isTrackedInDisplayList(
  tracked: { name: string; label?: string | null },
  display: (string | { name: string; label?: string | null })[]
): boolean {
  if (display.length === 0) return true;
  return display.some((d) => {
    if (typeof d === "string") {
      return d === tracked.name;
    }
    return displayMetricKeyEquals(
      { name: tracked.name, label: tracked.label },
      { name: d.name, label: d.label }
    );
  });
}

/** React keys / table column ids */
export function projectMetricKeyString(m: { name: string; label?: string | null }): string {
  return `${m.name}::${m.label ?? ""}`;
}

/** Tracked columns shown on Experiments / Kanban / DAG from project settings. */
export function getDisplayedTrackedMetrics(
  tracked: ProjectMetric[],
  display: ProjectDisplayMetric[]
): ProjectMetric[] {
  if (display.length === 0) {
    return tracked;
  }
  return tracked.filter((m) => isTrackedInDisplayList(
    { name: m.name, label: m.label },
    display
  ));
}

/** How a tracked row is stored in `displayMetrics` (legacy string = name only). */
export function trackedToDisplayKey(m: ProjectMetric): ProjectDisplayMetric {
  if (m.label == null || m.label === "") {
    return m.name;
  }
  return { name: m.name, label: m.label };
}

export function removeFromDisplayList(
  display: ProjectDisplayMetric[],
  metric: ProjectMetric
): ProjectDisplayMetric[] {
  return display.filter((d) => {
    if (typeof d === "string") {
      if (metric.label != null && metric.label !== "") {
        return true;
      }
      return d !== metric.name;
    }
    return !displayMetricKeyEquals(
      { name: d.name, label: d.label },
      { name: metric.name, label: metric.label }
    );
  });
}
