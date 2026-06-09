"use client";

import { TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatMetricLabel } from "@/lib/metrics/format-metric-label";
import {
  formatMetricScalarForDisplay,
  formatMetricScalarTooltipFull,
} from "@/lib/metrics/metric-value-display";
import {
  MetricDeltaVsParent,
  metricDeltaSplitModel,
} from "@/components/shared/metric-delta-vs-parent";

export type MetricValueDiffClusterOrder = "diff-first" | "value-first";

/**
 * Optional Tailwind (or other) classes merged onto specific layout nodes inside
 * {@link MetricNameValueDiffRow}. Use this from callers that need denser type, sidebar vs table
 * density, etc., without forking the component.
 */
export type MetricNameValueDiffRowClassNameProps = {
  /** Outermost wrapper (`flex`, or `contents` when the row is part of a parent metric table). */
  root?: string;
  /** Left column: wraps name + optional direction icon cluster. */
  nameCluster?: string;
  /** Inner flex row: truncated name + hint icons. */
  nameInnerCluster?: string;
  /** The truncated metric title span (when `showName`). */
  nameTrigger?: string;
  /** Lucide direction hint next to the name (`TrendingUp` / `TrendingDown`). */
  directionHint?: string;
  /** Right side: either the flex cluster (non-table) or the value/delta grid wrapper (table modes). */
  valueCluster?: string;
  /** Formatted scalar text (table and inline value). */
  valueText?: string;
  /** Signed Δ text in split table cells and inline `MetricDeltaVsParent` text span. */
  deltaText?: string;
  /** Outcome icon in split table cells and inline delta cluster. */
  deltaIcon?: string;
  /** Table layout only: grid cell for slot 1 (Δ or value, depending on `valueDiffClusterOrder`). */
  tableSlot1?: string;
  /** Table layout only: middle column wrapping the trend icon. */
  tableArrow?: string;
  /** Table layout only: grid cell for slot 2 (value or Δ). */
  tableSlot2?: string;
};

/** CSS grid class for the parent when each metric row uses `metricTable.scope === "group"` (one shared table). */
export function metricRowGroupTableClass(groupHasAnyDiff: boolean): string {
  return cn(
    "grid w-full items-center gap-x-1.5 gap-y-1.5",
    groupHasAnyDiff
      ? "grid-cols-[minmax(0,1fr)_auto_auto_auto]"
      : "grid-cols-[minmax(0,1fr)_auto]"
  );
}

/**
 * Enables the numeric **Δ | icon | value** layout (or the `valueDiffClusterOrder` swap).
 * `groupHasAnyDiff` drops the Δ columns when nothing in the set can compare to a parent.
 *
 * **`scope` is the main split:** is this row **part of one shared table** with other rows, or **one
 * box** on its own?
 *
 * - **`group`** — Part of the parent table: wrap sibling rows with {@link metricRowGroupTableClass}.
 *   This row uses `display: contents` so its pieces line up in **the same grid** as other metrics.
 *
 * - **`cell`** — One box: parent gives a single cell (or any container); this row draws its **own**
 *   mini-grid inside that box. Columns align only within that box.
 */
export type MetricNameValueDiffRowMetricTable =
  | {
      /** Row is a fragment of the parent metric table (shared columns). */
      scope: "group";
      /** Parent grid includes Δ + icon columns when any row in the group has value + parent. */
      groupHasAnyDiff: boolean;
    }
  | {
      /** Row is a self-contained block (e.g. one table cell), not merged into a parent metric grid. */
      scope: "cell";
      /** Same as `group`: use split Δ layout when the surrounding rows have any diffs. */
      groupHasAnyDiff: boolean;
    };

export type MetricNameValueDiffRowProps = {
  metricName: string;
  metricLabel?: string | null;
  /** Shown in the name cell when `showName`; hover uses {@link formatMetricLabel} for the full label. */
  nameTitleMode?: "full" | "name-only";
  value: number | null | undefined;
  parentValue?: number | null;
  direction: "maximize" | "minimize";
  showName?: boolean;
  showDiff?: boolean;
  showDirectionHint?: boolean;
  /**
   * `diff-first`: Δ (right) | icon | value (left) in table layout.
   * `value-first`: value (right) | icon | Δ (left) in table layout.
   */
  valueDiffClusterOrder?: MetricValueDiffClusterOrder;
  /**
   * Table-style numbers (Δ | icon | value). **`scope`**: `group` = piece of a parent metric table
   * (wrap rows with {@link metricRowGroupTableClass}); `cell` = one self-contained box (e.g. a
   * single table cell). See {@link MetricNameValueDiffRowMetricTable} for `groupHasAnyDiff`.
   */
  metricTable?: MetricNameValueDiffRowMetricTable;
  /** When false, signed Δ and trend icon use muted styling (cell may still be highlighted). */
  colorizeDiffOutcome?: boolean;
  /** Per-node class overrides; see {@link MetricNameValueDiffRowClassNameProps}. */
  classNameProps?: MetricNameValueDiffRowClassNameProps;
  "data-testid"?: string;
};

function DeltaSignedCell({
  model,
  textClassName,
  colorizeOutcome = true,
}: {
  model: NonNullable<ReturnType<typeof metricDeltaSplitModel>>;
  textClassName?: string;
  colorizeOutcome?: boolean;
}) {
  const { outcomeClass, signedDisplay, fullDeltaText } = model;
  const diffColorClass = colorizeOutcome ? outcomeClass : "text-muted-foreground";
  return (
    <span
      title={fullDeltaText}
      className={cn(
        "inline-flex cursor-default touch-manipulation tabular-nums",
        textClassName,
        diffColorClass
      )}
    >
      {signedDisplay}
    </span>
  );
}

function DeltaIconCell({
  model,
  iconClassName,
  colorizeOutcome = true,
}: {
  model: NonNullable<ReturnType<typeof metricDeltaSplitModel>>;
  iconClassName?: string;
  colorizeOutcome?: boolean;
}) {
  const { DeltaIcon, outcomeClass, fullDeltaText } = model;
  const diffColorClass = colorizeOutcome ? outcomeClass : "text-muted-foreground";
  return (
    <span title={fullDeltaText} className="inline-flex cursor-default touch-manipulation justify-center">
      <DeltaIcon className={cn(iconClassName, diffColorClass)} aria-hidden />
    </span>
  );
}

export function MetricNameValueDiffRow({
  metricName,
  metricLabel = null,
  nameTitleMode = "full",
  value,
  parentValue = null,
  direction,
  showName = true,
  showDiff = true,
  showDirectionHint = false,
  valueDiffClusterOrder = "diff-first",
  metricTable,
  colorizeDiffOutcome = true,
  classNameProps,
  "data-testid": dataTestId,
}: MetricNameValueDiffRowProps) {
  const c = classNameProps ?? {};
  const fullMetricName = formatMetricLabel(metricName, metricLabel);
  const title = nameTitleMode === "name-only" ? metricName : fullMetricName;
  const hasNameColumn = showName || showDirectionHint;

  const splitModel =
    showDiff && metricTable
      ? metricDeltaSplitModel(value ?? null, parentValue ?? null, direction)
      : null;

  const valueSpanClass = (align: "right" | "left" | "solo-right") =>
    cn(
      "cursor-default font-mono text-xs tabular-nums",
      align === "right" && "inline-block min-w-[5ch] text-right",
      align === "left" && "inline-block min-w-[5ch] text-left",
      align === "solo-right" && "inline-block min-w-[5ch] text-right",
      c.valueText,
      value === null || value === undefined ? "text-muted-foreground" : ""
    );

  const valueTooltipText = formatMetricScalarTooltipFull(value);

  const valueNode = (align: "right" | "left" | "solo-right") => (
    <span className={valueSpanClass(align)} title={valueTooltipText}>
      {formatMetricScalarForDisplay(value)}
    </span>
  );

  const diffNodeInline = showDiff ? (
    <MetricDeltaVsParent
      value={value ?? null}
      parentValue={parentValue ?? null}
      direction={direction}
      textClassName={c.deltaText}
      iconClassName={c.deltaIcon}
      colorizeOutcome={colorizeDiffOutcome}
      iconFirst={valueDiffClusterOrder === "value-first"}
    />
  ) : null;

  const nameInnerTable = Boolean(metricTable && hasNameColumn);

  const nameBlock =
    hasNameColumn ? (
      <div className={cn("flex min-w-0 flex-1 items-center overflow-hidden", c.nameCluster)}>
        <div
          className={cn(
            "mr-auto flex w-max min-w-0 max-w-full items-center gap-2 overflow-hidden",
            nameInnerTable && "mr-0 w-full max-w-none",
            c.nameInnerCluster
          )}
        >
          {showName ? (
            <span
              title={fullMetricName}
              className={cn(
                "min-w-0 max-w-full shrink cursor-default truncate text-left",
                c.nameTrigger
              )}
            >
              {title}
            </span>
          ) : null}
          {showDirectionHint ? (
            direction === "minimize" ? (
              <TrendingDown
                className={cn("h-3 w-3 shrink-0 text-muted-foreground", c.directionHint)}
                aria-hidden
              />
            ) : (
              <TrendingUp
                className={cn("h-3 w-3 shrink-0 text-muted-foreground", c.directionHint)}
                aria-hidden
              />
            )
          ) : null}
        </div>
      </div>
    ) : null;

  /** Table: first slot (Δ or value), arrow, second slot (value or Δ). */
  const tableTriple = (groupStyle: boolean) => {
    const gh = metricTable?.groupHasAnyDiff ?? false;
    if (!gh) {
      return (
        <div
          className={cn(
            groupStyle ? "flex min-w-0 justify-end" : "flex min-w-0 w-full justify-end",
            c.valueCluster
          )}
        >
          {valueNode("solo-right")}
        </div>
      );
    }
    const vf = valueDiffClusterOrder === "value-first";
    const slot1 = vf ? valueNode("right") : splitModel ? (
      <DeltaSignedCell
        model={splitModel}
        textClassName={c.deltaText}
        colorizeOutcome={colorizeDiffOutcome}
      />
    ) : (
      <span className={cn("inline-block min-w-[5ch]", c.tableSlot1)} aria-hidden />
    );
    const slot2 = vf
      ? splitModel
        ? (
            <DeltaSignedCell
              model={splitModel}
              textClassName={c.deltaText}
              colorizeOutcome={colorizeDiffOutcome}
            />
          )
        : null
      : valueNode("left");
    const arrow = splitModel ? (
      <DeltaIconCell
        model={splitModel}
        iconClassName={c.deltaIcon}
        colorizeOutcome={colorizeDiffOutcome}
      />
    ) : (
      <span className={cn("inline-flex w-3 shrink-0 justify-center", c.tableArrow)} aria-hidden />
    );

    const inner = (
      <>
        <div
          className={cn(
            "flex min-w-0 items-center justify-end",
            groupStyle ? "" : "justify-self-end",
            c.tableSlot1
          )}
        >
          {slot1}
        </div>
        <div className={cn("flex shrink-0 items-center justify-center", c.tableArrow)}>{arrow}</div>
        <div
          className={cn(
            "flex min-w-0 items-center justify-start",
            groupStyle ? "" : "justify-self-start",
            c.tableSlot2
          )}
        >
          {slot2}
        </div>
      </>
    );

    if (groupStyle) {
      return <div className={cn("contents", c.valueCluster)}>{inner}</div>;
    }
    return (
      <div
        className={cn(
          "grid w-full min-w-0 items-center gap-x-1 [grid-template-columns:minmax(0,1fr)_auto_minmax(0,1fr)]",
          c.valueCluster
        )}
      >
        {inner}
      </div>
    );
  };

  const valueClusterFlex = (
    <div
      className={cn("flex shrink-0 items-center justify-end gap-0.5", c.valueCluster)}
    >
      {valueDiffClusterOrder === "value-first" ? (
        <>
          {valueNode("solo-right")}
          {diffNodeInline}
        </>
      ) : (
        <>
          {diffNodeInline}
          {valueNode("solo-right")}
        </>
      )}
    </div>
  );

  if (metricTable?.scope === "group" && hasNameColumn) {
    const gh = metricTable.groupHasAnyDiff;
    return (
      <div className={cn("contents", c.root)} data-testid={dataTestId}>
        {nameBlock}
        {gh ? tableTriple(true) : (
          <div className={cn("flex min-w-0 justify-end", c.valueCluster)}>{valueNode("solo-right")}</div>
        )}
      </div>
    );
  }

  if (metricTable?.scope === "cell") {
    const gh = metricTable.groupHasAnyDiff;
    return (
      <div className={cn("min-w-0", c.root)} data-testid={dataTestId}>
        {gh ? tableTriple(false) : (
          <div className={cn("flex w-full justify-end", c.valueCluster)}>{valueNode("solo-right")}</div>
        )}
      </div>
    );
  }

  return (
    <div className={cn("flex min-w-0 items-center", c.root)} data-testid={dataTestId}>
      {nameBlock}
      {valueClusterFlex}
    </div>
  );
}
