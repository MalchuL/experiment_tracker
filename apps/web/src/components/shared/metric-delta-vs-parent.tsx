import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp, Equal } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  formatMetricScalarForEditorFull,
  formatMetricSignedDeltaForDisplay,
  metricIsBetterThanParent,
  metricSignedDeltaIsDisplayTie,
} from "@/lib/metrics/metric-value-display";

export function metricDeltaOutcomeColorClass(isBetter: boolean | null): string {
  return isBetter === true
    ? "text-green-500"
    : isBetter === false
      ? "text-red-500"
      : "text-muted-foreground";
}

/** Shared numbers for inline and table-split delta rendering. */
export type MetricDeltaSplitModel = {
  delta: number;
  tie: boolean;
  DeltaIcon: LucideIcon;
  outcomeClass: string;
  signedDisplay: string;
  fullDeltaText: string;
};

export function metricDeltaSplitModel(
  value: number | null,
  parentValue: number | null,
  direction: "maximize" | "minimize"
): MetricDeltaSplitModel | null {
  if (value === null || parentValue === null) return null;
  const delta = value - parentValue;
  const tie = metricSignedDeltaIsDisplayTie(delta);
  const DeltaIcon = tie ? Equal : delta > 0 ? TrendingUp : TrendingDown;
  const isBetter = metricIsBetterThanParent(value, parentValue, direction);
  const outcomeClass = metricDeltaOutcomeColorClass(isBetter);
  const signedDisplay = formatMetricSignedDeltaForDisplay(delta);
  const fullDeltaText = Number.isFinite(delta) ? formatMetricScalarForEditorFull(delta) : "—";
  return { delta, tie, DeltaIcon, outcomeClass, signedDisplay, fullDeltaText };
}

export function MetricDeltaVsParent({
  value,
  parentValue,
  direction,
  textClassName = "font-mono text-[9px] tabular-nums leading-none",
  iconClassName = "w-2.5 h-2.5 shrink-0",
  colorizeOutcome = true,
  /**
   * `false` (default): signed Δ then outcome icon (e.g. diff-first: … | signed | icon | value).
   * `true`: icon then signed Δ (use with value-first: value | icon | signed).
   */
  iconFirst = false,
}: {
  value: number | null;
  parentValue: number | null;
  direction: "maximize" | "minimize";
  /** Tailwind text size; sidebar can pass e.g. `text-xs`. */
  textClassName?: string;
  iconClassName?: string;
  /** When false, Δ text and icon use muted styling instead of better/worse colors. */
  colorizeOutcome?: boolean;
  iconFirst?: boolean;
}) {
  const model = metricDeltaSplitModel(value, parentValue, direction);
  if (!model) return null;
  const { DeltaIcon, outcomeClass, signedDisplay, fullDeltaText } = model;
  const diffColorClass = colorizeOutcome ? outcomeClass : "text-muted-foreground";
  const signed = <span className={cn(textClassName, diffColorClass)}>{signedDisplay}</span>;
  const icon = <DeltaIcon className={cn(iconClassName, diffColorClass)} aria-hidden />;

  return (
    <span
      title={fullDeltaText}
      className="inline-flex cursor-default touch-manipulation items-center gap-0.5"
    >
      {iconFirst ? (
        <>
          {icon}
          {signed}
        </>
      ) : (
        <>
          {signed}
          {icon}
        </>
      )}
    </span>
  );
}
