"use client";

import type { Dispatch, SetStateAction } from "react";
import { format } from "date-fns";
import { Checkbox } from "@/components/ui/checkbox";
import type { HeaderContext } from "@tanstack/react-table";
import { cn } from "@/lib/utils";
import type { MetricsTableRow } from "../lib/types";
import { formatMetricTableCellValue } from "../lib/format";
import { METRIC_CELL_TINTS, metricCellStyleKey } from "../lib/constants";

export function flipIdInSet(id: string, set: Set<string>): Set<string> {
  const s = new Set(set);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  return s;
}

type ExperimentColumnHeaderProps = {
  editMode: boolean;
  header: HeaderContext<MetricsTableRow, unknown>;
};

export function ExperimentColumnHeader({ editMode, header }: ExperimentColumnHeaderProps) {
  const col = header.column;
  return (
    <div className="w-full text-left">
      {editMode ? <span className="mb-0.5 block text-[10px] text-muted-foreground">In view</span> : null}
      <button
        type="button"
        className="flex w-full min-w-0 items-center gap-1 text-left font-medium"
        onClick={col.getToggleSortingHandler()}
      >
        Experiment{col.getIsSorted() === "asc" ? " ↑" : col.getIsSorted() === "desc" ? " ↓" : null}
      </button>
    </div>
  );
}

type ExperimentNameCellProps = {
  row: MetricsTableRow;
  editMode: boolean;
  hiddenRowIds: Set<string>;
  setHiddenRowIds: Dispatch<SetStateAction<Set<string>>>;
  onSelectExperiment: (experimentId: string) => void;
};

export function ExperimentNameCell({
  row,
  editMode,
  hiddenRowIds,
  setHiddenRowIds,
  onSelectExperiment,
}: ExperimentNameCellProps) {
  const namePart = (
    <div className="min-w-0 min-h-[1.5rem] flex-1 text-left">
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
        <span className="min-w-0 font-medium" title={row.experimentName}>
          {row.experimentName}
        </span>
      </div>
    </div>
  );
  if (editMode) {
    return (
      <div className="flex min-w-0 items-start gap-2 pr-2">
        <div className="pt-0.5" onClick={(e) => e.stopPropagation()}>
          <Checkbox
            className="shrink-0"
            checked={!hiddenRowIds.has(row.experimentId)}
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
        {namePart}
      </div>
    );
  }
  return <div className="flex min-w-0 pr-2">{namePart}</div>;
}

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
  if (editMode) {
    return (
      <div
        className="flex w-full min-w-0 flex-col items-stretch gap-1.5 text-right"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-wrap items-center justify-end gap-3 text-[10px] text-muted-foreground">
          <label className="flex cursor-pointer items-center gap-0.5">
            <Checkbox
              checked={!hiddenColumnIds.has(n)}
              onCheckedChange={() => setHiddenColumnIds((p) => flipIdInSet(n, p))}
            />
            <span>Col</span>
          </label>
          <label className="flex cursor-pointer items-center gap-0.5">
            <Checkbox
              checked={minHighlightColumnIds.has(n)}
              onCheckedChange={() => setMinHighlightColumnIds((p) => flipIdInSet(n, p))}
            />
            <span>Min</span>
          </label>
          <label className="flex cursor-pointer items-center gap-0.5">
            <Checkbox
              checked={maxHighlightColumnIds.has(n)}
              onCheckedChange={() => setMaxHighlightColumnIds((p) => flipIdInSet(n, p))}
            />
            <span>Max</span>
          </label>
        </div>
        <button
          type="button"
          className="flex w-full min-w-0 items-center justify-end gap-1 font-medium"
          onClick={ctx.getToggleSortingHandler()}
        >
          <span className="whitespace-nowrap" title={n}>
            {n}
          </span>
          {ctx.getIsSorted() === "asc" ? " ↑" : ctx.getIsSorted() === "desc" ? " ↓" : null}
        </button>
      </div>
    );
  }
  return (
    <button
      type="button"
      className="flex w-full items-end justify-end gap-1"
      onClick={ctx.getToggleSortingHandler()}
    >
      <span className="block w-full whitespace-nowrap text-right">{n}</span>
      {ctx.getIsSorted() === "asc" ? " ↑" : ctx.getIsSorted() === "desc" ? " ↓" : null}
    </button>
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
}: MetricValueCellProps) {
  const mm = colMinMax[n];
  const isBold =
    (minHighlightColumnIds.has(n) && v != null && Number.isFinite(v) && mm != null && v === mm.min) ||
    (maxHighlightColumnIds.has(n) && v != null && Number.isFinite(v) && mm != null && v === mm.max);
  const tint = cellTints[metricCellStyleKey(row, n)];
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => cycleCellTint(row.experimentId, n)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          cycleCellTint(row.experimentId, n);
        }
      }}
      className={cn(
        "text-right font-mono text-sm rounded px-0.5 -mx-0.5",
        "cursor-pointer outline-offset-1 hover:ring-1 hover:ring-border",
        isBold && "font-bold",
        tint != null ? METRIC_CELL_TINTS[tint] : ""
      )}
    >
      {formatMetricTableCellValue(v)}
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
        title="Read-only when shown — not sortable"
      >
        experimentId
      </div>
    ) : (
      <div
        className="font-mono text-xs sm:text-sm text-muted-foreground/90"
        title="Read-only when shown — not sortable"
      >
        createdAt
      </div>
    );
  if (editMode) {
    return (
      <div className="w-full min-w-0 text-right" onClick={(e) => e.stopPropagation()}>
        <div className="mb-0.5 flex flex-wrap items-center justify-end text-[10px] text-muted-foreground">
          <label className="flex cursor-pointer items-center gap-0.5">
            <Checkbox
              checked={!hiddenColumnIds.has(columnId)}
              onCheckedChange={() => setHiddenColumnIds((p) => flipIdInSet(columnId, p))}
            />
            <span>Col</span>
          </label>
        </div>
        {label}
      </div>
    );
  }
  return (
    <div
      className="w-full min-w-0 text-right text-muted-foreground/90 opacity-80"
      title="Read-only when shown — not sortable"
    >
      <span className="font-mono text-xs sm:text-sm">{columnId === "experimentId" ? "experimentId" : "createdAt"}</span>
    </div>
  );
}

type ExperimentIdCellProps = {
  value: string;
};

export function ExperimentIdCell({ value }: ExperimentIdCellProps) {
  return (
    <div className="pr-2 text-right font-mono text-xs text-muted-foreground/90 select-text" title={value}>
      {value}
    </div>
  );
}

type CreatedAtCellProps = {
  raw: string;
};

export function CreatedAtCell({ raw }: CreatedAtCellProps) {
  if (!raw) {
    return <div className="pr-2 text-right text-sm text-muted-foreground/80 select-text">—</div>;
  }
  let d: Date;
  try {
    d = new Date(raw);
    if (Number.isNaN(d.getTime())) throw new Error("invalid");
  } catch {
    return <div className="pr-2 text-right font-mono text-xs text-muted-foreground/80 select-text">{raw}</div>;
  }
  return (
    <div className="pr-2 text-right font-mono text-xs text-muted-foreground/90 select-text" title={raw}>
      {format(d, "yyyy-MM-dd HH:mm:ss")}
    </div>
  );
}
