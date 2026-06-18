import type { CSSProperties } from "react";

/** Drop shadow on pinned lead columns (layout only — not part of selection styling). */
export const STICKY_LEAD_COLUMN_SHADOW = "4px 0 12px -8px rgba(0,0,0,0.08)";

/** Selected row: tint + left accent bar (experiment name / primary lead cell). */
export function getExperimentSelectionSurfaceStyle(
  experimentColor: string | null | undefined
): CSSProperties {
  const c = experimentColor || "hsl(var(--primary))";
  return {
    backgroundColor: `color-mix(in srgb, ${c} 20%, var(--background))`,
    boxShadow: `inset 4px 0 0 0 ${c}`,
  };
}

/** Selected row: background tint only (grip, checkbox column, metric cells). */
export function getExperimentSelectionBackgroundStyle(
  experimentColor: string | null | undefined
): CSSProperties {
  return {
    backgroundColor: getExperimentSelectionSurfaceStyle(experimentColor).backgroundColor,
  };
}

export type ExperimentSelectionMetricsCellRole =
  | "grip"
  | "showInReport"
  | "experiment"
  | "metric";

/** Same selection chrome in every pin mode — pin only affects sticky `left` / layout classes. */
export function getExperimentSelectionMetricsCellStyle(
  role: ExperimentSelectionMetricsCellRole,
  isSelected: boolean,
  experimentColor: string | null | undefined
): CSSProperties | undefined {
  if (!isSelected) return undefined;
  if (role === "experiment") return getExperimentSelectionSurfaceStyle(experimentColor);
  return getExperimentSelectionBackgroundStyle(experimentColor);
}
