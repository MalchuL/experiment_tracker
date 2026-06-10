import type { MetricNameValueDiffRowClassNameProps } from "@/components/shared/metric-name-value-diff-row";
import { metricRowGroupTableClass } from "@/components/shared/metric-name-value-diff-row";
import { cn } from "@/lib/utils";

export const METRIC_SIDEBAR_ROW_SEPARATOR_CLASS = "border-b border-border/35 py-1";

/** Shared row density for Project Metrics and Logged Metrics in the experiment sidebar. */
export const METRIC_SIDEBAR_DENSE_CLASS_NAMES = {
  root: "text-sm",
  nameCluster: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  valueCluster: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableSlot1: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableArrow: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableSlot2: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  deltaText: "font-mono text-xs tabular-nums leading-none",
  deltaIcon: "w-2.5 h-2.5",
} satisfies MetricNameValueDiffRowClassNameProps;

export const METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES = {
  ...METRIC_SIDEBAR_DENSE_CLASS_NAMES,
  root: "text-sm pl-0",
} satisfies MetricNameValueDiffRowClassNameProps;

/** Matches {@link MetricNameValueDiffRow} value cell typography in sidebar table layout. */
export const METRIC_SIDEBAR_VALUE_DISPLAY_CLASS =
  "inline-block min-w-[5ch] font-mono text-xs tabular-nums leading-none text-right";

export const METRIC_SIDEBAR_VALUE_INPUT_CLASS =
  "h-auto min-h-0 min-w-[5ch] max-w-full border-transparent bg-transparent px-0 py-0 font-mono text-xs tabular-nums leading-none shadow-none hover:border-input focus-visible:border-input focus-visible:ring-1";

export const METRIC_SIDEBAR_ROW_REMOVE_CELL_CLASS = cn(
  METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  "flex items-center justify-end"
);

/** Matches dense sidebar metric row line height (text-sm / text-xs + py-1). */
export const METRIC_SIDEBAR_ROW_REMOVE_BUTTON_CLASS =
  "h-5 w-5 shrink-0 p-0 text-muted-foreground hover:text-destructive";

export const METRIC_SIDEBAR_ROW_REMOVE_ICON_CLASS = "h-3 w-3";

/** Logged-metrics grid; adds a trailing remove column when edit mode is on. */
export function loggedMetricRowGroupTableClass(
  groupHasAnyDiff: boolean,
  editMode: boolean
): string {
  if (!editMode) {
    return metricRowGroupTableClass(groupHasAnyDiff);
  }
  return cn(
    "grid w-full items-center gap-x-1.5 gap-y-1.5",
    groupHasAnyDiff
      ? "grid-cols-[minmax(0,1fr)_auto_auto_auto_1.25rem]"
      : "grid-cols-[minmax(0,1fr)_auto_1.25rem]"
  );
}
