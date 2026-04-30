import type { CSSProperties } from "react";

/** Same visual strategy as project metrics table rows (selected experiment). */
export function getExperimentSelectionSurfaceStyle(
  experimentColor: string | null | undefined
): CSSProperties {
  const c = experimentColor || "hsl(var(--primary))";
  return {
    backgroundColor: `color-mix(in srgb, ${c} 20%, var(--background))`,
    boxShadow: `inset 4px 0 0 0 ${c}`,
  };
}
