"use client";

import type { Dispatch, SetStateAction } from "react";
import { format, isValid, parseISO } from "date-fns";
import { Checkbox } from "@/components/ui/checkbox";
import type { HeaderContext } from "@tanstack/react-table";
import { cn } from "@/lib/utils";
import type { MetricsTableRow } from "../lib/types";
import { formatMetricTableCellValue } from "../lib/format";
import { METRIC_CELL_TINTS, metricCellStyleKey } from "../lib/constants";
import { formatMetricScalarTooltipFull } from "@/lib/metrics/metric-value-display";

export function flipIdInSet(id: string, set: Set<string>): Set<string> {
  const s = new Set(set);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  return s;
}

function EditModeCheckboxRow({
  id,
  label,
  checked,
  onCheckedChange,
  align = "start",
}: {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  align?: "start" | "end";
}) {
  const checkbox = (
    <Checkbox
      id={id}
      className="shrink-0"
      checked={checked}
      onCheckedChange={(c) => onCheckedChange(c === true)}
    />
  );
  const text = (
    <span className={cn("min-w-0 truncate", align === "end" ? "text-right" : "text-left")}>{label}</span>
  );

  return (
    <label
      htmlFor={id}
      className={cn(
        "flex min-w-0 cursor-pointer items-center gap-2 rounded-sm py-0.5 text-[11px] leading-tight text-muted-foreground hover:text-foreground",
        align === "end" ? "w-full justify-end" : "w-full justify-start"
      )}
    >
      {align === "end" ? (
        <>
          {text}
          {checkbox}
        </>
      ) : (
        <>
          {checkbox}
          {text}
        </>
      )}
    </label>
  );
}

type ExperimentColumnHeaderProps = {
  header: HeaderContext<MetricsTableRow, unknown>;
};

export function ExperimentColumnHeader({ header }: ExperimentColumnHeaderProps) {
  const col = header.column;
  const experimentHeaderFullLabel = `Experiment${
    col.getIsSorted() === "asc" ? " ↑" : col.getIsSorted() === "desc" ? " ↓" : ""
  }`;
  return (
    <div className="w-full min-w-0 overflow-hidden text-left">
      <button
        type="button"
        className="flex w-full min-w-0 items-center gap-1 text-left font-medium"
        title={experimentHeaderFullLabel}
        onClick={col.getToggleSortingHandler()}
      >
        <span className="block min-w-0 flex-1 truncate">{experimentHeaderFullLabel}</span>
      </button>
    </div>
  );
}

type ShowInReportCellProps = {
  row: MetricsTableRow;
  hiddenRowIds: Set<string>;
  setHiddenRowIds: Dispatch<SetStateAction<Set<string>>>;
};

export function ShowInReportCell({ row, hiddenRowIds, setHiddenRowIds }: ShowInReportCellProps) {
  return (
    <div className="flex h-full items-center justify-center px-0" onClick={(e) => e.stopPropagation()}>
      <Checkbox
        className="shrink-0"
        checked={!hiddenRowIds.has(row.experimentId)}
        aria-label={`Show ${row.experimentName} in report`}
        onCheckedChange={(v) => {
          setHiddenRowIds((prev) => {
            const s = new Set(prev);
            if (v === true) s.delete(row.experimentId);
            else s.add(row.experimentId);
            return s;
          });
        }}
      />
    </div>
  );
}

type ExperimentNameCellProps = {
  row: MetricsTableRow;
  onSelectExperiment: (experimentId: string) => void;
  wrapExperimentNames: boolean;
};

export function ExperimentNameCell({
  row,
  onSelectExperiment,
  wrapExperimentNames,
}: ExperimentNameCellProps) {
  return (
    <div className="flex w-full min-w-0 pr-2">
      <div
        className={cn(
          "min-w-0 min-h-[1.5rem] flex-1 overflow-hidden text-left",
          wrapExperimentNames ? "whitespace-normal break-words [overflow-wrap:anywhere]" : "whitespace-nowrap"
        )}
      >
        <div
          className="flex w-full min-w-0 cursor-pointer items-center gap-2 rounded-sm px-0.5 -mx-0.5 py-0.5 text-left outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => onSelectExperiment(row.experimentId)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelectExperiment(row.experimentId);
            }
          }}
          role="button"
          tabIndex={0}
          title="Open experiment details"
        >
          <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: row.experimentColor }} aria-hidden />
          <span
            className={cn("block min-w-0 flex-1 font-medium", !wrapExperimentNames && "truncate")}
            title={row.experimentName}
          >
            {row.experimentName}
          </span>
        </div>
      </div>
    </div>
  );
}

/** Reserve space for the column-resize handle (w-2.5) in edit-mode headers only. */
const METRIC_HEADER_EDIT_RESIZE_GUTTER = "pr-2.5";

type MetricColumnHeaderProps = {
  name: string;
  editMode: boolean;
  header: HeaderContext<MetricsTableRow, unknown>;
  hiddenColumnIds: Set<string>;
  setHiddenColumnIds: Dispatch<SetStateAction<Set<string>>>;
  minHighlightColumnIds: Set<string>;
  setMinHighlightColumnIds: Dispatch<SetStateAction<Set<string>>>;
  maxHighlightColumnIds: Set<string>;
  setMaxHighlightColumnIds: Dispatch<SetStateAction<Set<string>>>;
};

export function MetricColumnHeader({
  name: n,
  editMode,
  header,
  hiddenColumnIds,
  setHiddenColumnIds,
  minHighlightColumnIds,
  setMinHighlightColumnIds,
  maxHighlightColumnIds,
  setMaxHighlightColumnIds,
}: MetricColumnHeaderProps) {
  const ctx = header.column;
  const sortSuffix = ctx.getIsSorted() === "asc" ? " ↑" : ctx.getIsSorted() === "desc" ? " ↓" : "";
  const nameLabel = (
    <button
      type="button"
      className="flex w-full min-w-0 items-center justify-end gap-1 font-medium"
      title={`${n}${sortSuffix}`}
      onClick={ctx.getToggleSortingHandler()}
    >
      <span className="block min-w-0 flex-1 truncate text-right" title={n}>
        {n}
      </span>
      {sortSuffix ? <span className="shrink-0">{sortSuffix}</span> : null}
    </button>
  );
  if (editMode) {
    return (
      <div
        className={cn(
          "flex w-full min-w-0 flex-col items-stretch gap-2 text-right",
          METRIC_HEADER_EDIT_RESIZE_GUTTER
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex w-full flex-col items-end gap-1 pb-2">
          <EditModeCheckboxRow
            id={`col-visible-${n}`}
            label="Show column"
            checked={!hiddenColumnIds.has(n)}
            onCheckedChange={() => setHiddenColumnIds((p) => flipIdInSet(n, p))}
            align="end"
          />
          <EditModeCheckboxRow
            id={`col-min-${n}`}
            label="Highlight min"
            checked={minHighlightColumnIds.has(n)}
            onCheckedChange={() => setMinHighlightColumnIds((p) => flipIdInSet(n, p))}
            align="end"
          />
          <EditModeCheckboxRow
            id={`col-max-${n}`}
            label="Highlight max"
            checked={maxHighlightColumnIds.has(n)}
            onCheckedChange={() => setMaxHighlightColumnIds((p) => flipIdInSet(n, p))}
            align="end"
          />
        </div>
        <div className="w-full border-t border-border/60 pt-2">{nameLabel}</div>
      </div>
    );
  }
  return (
    <div className="w-full min-w-0 overflow-hidden">
      <button
        type="button"
        className="flex w-full min-w-0 items-end justify-end gap-1"
        title={`${n}${sortSuffix}`}
        onClick={ctx.getToggleSortingHandler()}
      >
        <span className="block min-w-0 flex-1 truncate text-right" title={n}>
          {n}
        </span>
        {sortSuffix ? <span className="shrink-0">{sortSuffix}</span> : null}
      </button>
    </div>
  );
}

type MetricValueCellProps = {
  row: MetricsTableRow;
  metricName: string;
  value: number | null;
  colMinMax: Record<string, { min: number; max: number }>;
  minHighlightColumnIds: Set<string>;
  maxHighlightColumnIds: Set<string>;
  cellTints: Record<string, 1 | 2 | 3 | 4>;
  cycleCellTint: (experimentId: string, metricName: string) => void;
  wrapValues: boolean;
};

export function MetricValueCell({
  row,
  metricName: n,
  value: v,
  colMinMax,
  minHighlightColumnIds,
  maxHighlightColumnIds,
  cellTints,
  cycleCellTint,
  wrapValues,
}: MetricValueCellProps) {
  const mm = colMinMax[n];
  const isBold =
    (minHighlightColumnIds.has(n) && v != null && Number.isFinite(v) && mm != null && v === mm.min) ||
    (maxHighlightColumnIds.has(n) && v != null && Number.isFinite(v) && mm != null && v === mm.max);
  const tint = cellTints[metricCellStyleKey(row, n)];
  const formatted = formatMetricTableCellValue(v);
  return (
    <div
      role="button"
      tabIndex={0}
      title={formatMetricScalarTooltipFull(v)}
      onClick={() => cycleCellTint(row.experimentId, n)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          cycleCellTint(row.experimentId, n);
        }
      }}
      className={cn(
        "min-w-0 text-right font-mono text-sm tabular-nums px-0.5 -mx-0.5",
        "cursor-pointer outline-offset-1 hover:ring-1 hover:ring-border",
        wrapValues ? "whitespace-normal break-words" : "overflow-hidden whitespace-nowrap",
        isBold && "font-bold",
        tint != null ? METRIC_CELL_TINTS[tint] : ""
      )}
    >
      <span className={cn("block min-w-0", !wrapValues && "truncate")}>{formatted}</span>
    </div>
  );
}

type ReadonlyMetaColumnHeaderProps = {
  columnId: "experimentId" | "createdAt";
  editMode: boolean;
  hiddenColumnIds: Set<string>;
  setHiddenColumnIds: Dispatch<SetStateAction<Set<string>>>;
};

export function ReadonlyMetaColumnHeader({
  columnId,
  editMode,
  hiddenColumnIds,
  setHiddenColumnIds,
}: ReadonlyMetaColumnHeaderProps) {
  const label =
    columnId === "experimentId" ? (
      <div
        className="font-mono text-xs sm:text-sm text-muted-foreground/90"
        title="experimentId — Read-only when shown — not sortable"
      >
        experimentId
      </div>
    ) : (
      <div
        className="font-mono text-xs sm:text-sm text-muted-foreground/90"
        title="createdAt — Read-only when shown — not sortable"
      >
        createdAt
      </div>
    );
  if (editMode) {
    return (
      <div
        className={cn("w-full min-w-0 text-right", METRIC_HEADER_EDIT_RESIZE_GUTTER)}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex w-full flex-col items-end pb-2">
          <EditModeCheckboxRow
            id={`col-visible-${columnId}`}
            label="Show column"
            checked={!hiddenColumnIds.has(columnId)}
            onCheckedChange={() => setHiddenColumnIds((p) => flipIdInSet(columnId, p))}
            align="end"
          />
        </div>
        <div className="border-t border-border/60 pt-2">{label}</div>
      </div>
    );
  }
  return (
    <div
      className="w-full min-w-0 overflow-hidden text-right text-muted-foreground/90 opacity-80"
      title={
        columnId === "experimentId"
          ? "experimentId — Read-only when shown — not sortable"
          : "createdAt — Read-only when shown — not sortable"
      }
    >
      <span className="font-mono text-xs sm:text-sm">{columnId === "experimentId" ? "experimentId" : "createdAt"}</span>
    </div>
  );
}

type ExperimentIdCellProps = {
  value: string;
  wrapValues: boolean;
};

export function ExperimentIdCell({ value, wrapValues }: ExperimentIdCellProps) {
  return (
    <div
      className={cn(
        "min-w-0 pr-2 text-right font-mono text-xs text-muted-foreground/90 select-text",
        wrapValues ? "whitespace-normal break-all" : "overflow-hidden whitespace-nowrap"
      )}
      title={value}
    >
      <span className={cn("block min-w-0", !wrapValues && "truncate")}>{value}</span>
    </div>
  );
}

type CreatedAtCellProps = {
  raw: string;
  wrapValues: boolean;
};

export function CreatedAtCell({ raw, wrapValues }: CreatedAtCellProps) {
  const truncateClass = wrapValues ? undefined : "truncate";
  const cellClass = cn(
    "min-w-0 pr-2 text-right select-text",
    wrapValues ? "whitespace-normal break-words" : "overflow-hidden whitespace-nowrap"
  );
  if (!raw) {
    return (
      <div className={cn(cellClass, "text-sm text-muted-foreground/80")}>
        <span className={cn("block min-w-0", truncateClass)}>—</span>
      </div>
    );
  }
  let d: Date;
  try {
    d = parseISO(raw);
    if (!isValid(d)) throw new Error("invalid");
  } catch {
    return (
      <div className={cn(cellClass, "font-mono text-xs text-muted-foreground/80")} title={raw}>
        <span className={cn("block min-w-0", truncateClass)}>{raw}</span>
      </div>
    );
  }
  const formatted = format(d, "yyyy-MM-dd HH:mm:ss");
  return (
    <div className={cn(cellClass, "font-mono text-xs text-muted-foreground/90")} title={raw}>
      <span className={cn("block min-w-0", truncateClass)}>{formatted}</span>
    </div>
  );
}
