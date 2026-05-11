import { TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  formatMetricSignedDeltaForDisplay,
  metricIsBetterThanParent,
} from "@/lib/metrics/metric-value-display";

const TIE_EPS = 1e-10;

export function metricDeltaOutcomeColorClass(isBetter: boolean | null): string {
  return isBetter === true
    ? "text-green-500"
    : isBetter === false
      ? "text-red-500"
      : "text-muted-foreground";
}

export function MetricDeltaVsParent({
  value,
  parentValue,
  direction,
  textClassName = "font-mono text-[9px] tabular-nums leading-none",
  iconClassName = "w-2.5 h-2.5 shrink-0",
}: {
  value: number | null;
  parentValue: number | null;
  direction: "maximize" | "minimize";
  /** Tailwind text size; sidebar can pass e.g. `text-xs`. */
  textClassName?: string;
  iconClassName?: string;
}) {
  if (value === null || parentValue === null) return null;
  const delta = value - parentValue;
  const tie = Math.abs(delta) < TIE_EPS;
  const ArrowIcon = tie ? null : delta > 0 ? TrendingUp : TrendingDown;
  const isBetter = metricIsBetterThanParent(value, parentValue, direction);
  const oc = metricDeltaOutcomeColorClass(isBetter);

  return (
    <>
      {ArrowIcon ? <ArrowIcon className={cn(iconClassName, oc)} /> : null}
      <span className={cn(textClassName, oc)}>{formatMetricSignedDeltaForDisplay(delta)}</span>
    </>
  );
}
