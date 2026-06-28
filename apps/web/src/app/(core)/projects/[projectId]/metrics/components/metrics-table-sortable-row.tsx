"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { flexRender, type Column, type Row, type Table as TTable } from "@tanstack/react-table";
import type { CSSProperties } from "react";
import { GripVertical } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { EXPERIMENTS_TABLE_GRIP_PX } from "@/domain/experiments/lib/experiments-table-column-widths";
import { getExperimentSelectionMetricsCellStyle } from "@/domain/experiments/experiment-selection-style";
import { ExperimentSelectionOrderBadge } from "@/domain/experiments/components/experiment-selection-order-badge";
import { SHOW_IN_REPORT_COLUMN_ID, SHOW_IN_REPORT_COLUMN_PX, METRICS_TABLE_ROW_BORDER_CLASS } from "../lib/constants";
import type { MetricsTableRow } from "../lib/types";

const GRIP_LEAD_SLOT_CLASS = "flex h-6 w-6 shrink-0 items-center justify-center";

const stickyLeadShadowClass = "shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)]";

const stickyGripCell = cn(
  "sticky left-0 z-[2] bg-background box-border overflow-hidden",
  stickyLeadShadowClass
);
const stickyExperimentCell = cn("sticky z-[2] bg-background box-border", stickyLeadShadowClass);
const stickyShowInReportCell = cn("sticky z-[2] bg-background box-border", stickyLeadShadowClass);

type MetricsTableSortableRowProps = {
  row: Row<MetricsTableRow>;
  table: TTable<MetricsTableRow>;
  isRowSelected: boolean;
  pinLeadColumns: boolean;
  leadColumnCount: number;
  gripWidthPx: number;
  rowReorderDisabled: boolean;
  editMode: boolean;
  selectionMode: boolean;
  selectionOrderNumber?: number | null;
  onSelectionToggle?: () => void;
  wrapExperimentNames: boolean;
  wrapValues: boolean;
};

function layoutForColumn<T>(table: TTable<T>, column: Column<T, unknown>): { className: string; style: CSSProperties } {
  const width = column.getSize();
  return { className: "", style: { width, minWidth: width, maxWidth: width } };
}

function metricsCellRole(columnId: string): "showInReport" | "experiment" | "metric" {
  if (columnId === SHOW_IN_REPORT_COLUMN_ID) return "showInReport";
  if (columnId === "experiment") return "experiment";
  return "metric";
}

export function MetricsTableSortableRow({
  row,
  table,
  isRowSelected,
  pinLeadColumns,
  leadColumnCount,
  gripWidthPx,
  rowReorderDisabled,
  editMode,
  selectionMode,
  selectionOrderNumber = null,
  onSelectionToggle,
  wrapExperimentNames,
  wrapValues,
}: MetricsTableSortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: row.id,
    disabled: rowReorderDisabled || selectionMode,
  });

  const expColor = row.original.experimentColor;
  const transformStr = transform ? CSS.Transform.toString(transform) : undefined;

  const pinGrip = pinLeadColumns && leadColumnCount >= 1;
  const pinShowInReport = pinLeadColumns && leadColumnCount >= 2 && editMode;
  const pinExperiment = pinLeadColumns && leadColumnCount >= (editMode ? 3 : 2);
  const showInReportWidth = editMode
    ? (table.getColumn(SHOW_IN_REPORT_COLUMN_ID)?.getSize() ?? SHOW_IN_REPORT_COLUMN_PX)
    : 0;
  const experimentStickyLeft = gripWidthPx + (editMode ? showInReportWidth : 0);

  const rowStyle = {
    ...(transformStr ? { transform: transformStr } : {}),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const gripReorderTitle = selectionMode
    ? "Select for compare"
    : rowReorderDisabled
    ? "Clear the name filter and column sorting to reorder experiments"
    : "Reorder";

  return (
    <TableRow
      ref={setNodeRef}
      data-state={isRowSelected ? "selected" : undefined}
      className={cn("group hover:bg-transparent", isRowSelected ? "transition-colors" : undefined)}
      style={rowStyle}
    >
      <TableCell
        className={cn(
          "px-2 py-2 align-middle group-hover:bg-muted/50",
          METRICS_TABLE_ROW_BORDER_CLASS,
          pinGrip && stickyGripCell
        )}
        style={{
          width: gripWidthPx,
          minWidth: gripWidthPx,
          maxWidth: gripWidthPx,
          ...getExperimentSelectionMetricsCellStyle("grip", isRowSelected, expColor),
        }}
      >
        {selectionMode && onSelectionToggle ? (
          <div className={GRIP_LEAD_SLOT_CLASS} title={gripReorderTitle}>
            <ExperimentSelectionOrderBadge
              experimentId={row.original.experimentId}
              experimentName={row.original.experimentName}
              orderNumber={selectionOrderNumber}
              onToggle={onSelectionToggle}
            />
          </div>
        ) : (
          <div
            className={cn(
              GRIP_LEAD_SLOT_CLASS,
              rowReorderDisabled
                ? "cursor-not-allowed opacity-40"
                : "cursor-grab active:cursor-grabbing"
            )}
            title={gripReorderTitle}
            {...attributes}
            {...(rowReorderDisabled ? {} : listeners)}
          >
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
      </TableCell>
      {row.getVisibleCells().map((cell) => {
        const isExperiment = cell.column.id === "experiment";
        const isShowInReport = cell.column.id === SHOW_IN_REPORT_COLUMN_ID;
        const wrapCell = isExperiment ? wrapExperimentNames : isShowInReport ? false : wrapValues;
        const layout = layoutForColumn(table, cell.column);
        const cellStyle: CSSProperties = {
          ...layout.style,
          ...getExperimentSelectionMetricsCellStyle(
            metricsCellRole(cell.column.id),
            isRowSelected,
            expColor
          ),
        };

        if (pinShowInReport && isShowInReport) {
          cellStyle.left = gripWidthPx;
        } else if (pinExperiment && isExperiment) {
          cellStyle.left = experimentStickyLeft;
        }

        return (
          <TableCell
            key={cell.id}
            className={cn(
              METRICS_TABLE_ROW_BORDER_CLASS,
              "group-hover:bg-muted/50",
              isShowInReport ? "align-middle px-1 py-2" : "align-top",
              !isShowInReport &&
                (wrapCell ? "whitespace-normal break-words" : "overflow-hidden whitespace-nowrap"),
              pinShowInReport && isShowInReport && stickyShowInReportCell,
              pinExperiment && isExperiment && stickyExperimentCell,
              layout.className
            )}
            style={cellStyle}
          >
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </TableCell>
        );
      })}
    </TableRow>
  );
}
