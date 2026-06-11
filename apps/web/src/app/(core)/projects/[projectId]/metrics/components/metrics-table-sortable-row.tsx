"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { flexRender, type Column, type Row, type Table as TTable } from "@tanstack/react-table";
import type { CSSProperties } from "react";
import { GripVertical } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { EXPERIMENTS_TABLE_GRIP_PX } from "@/domain/experiments/lib/experiments-table-column-widths";
import { getExperimentSelectionSurfaceStyle } from "@/domain/experiments/experiment-selection-style";
import type { MetricsTableRow } from "../lib/types";

const GRIP_LEAD_SLOT_CLASS = "flex h-6 w-6 shrink-0 items-center justify-center";

const stickyGripCell = cn(
  "sticky left-0 z-[2] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);
const stickyExperimentCell = cn(
  "sticky z-[2] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border"
);

type MetricsTableSortableRowProps = {
  row: Row<MetricsTableRow>;
  table: TTable<MetricsTableRow>;
  isRowSelected: boolean;
  pinLeadColumns: boolean;
  leadColumnCount: number;
  gripWidthPx: number;
  rowReorderDisabled: boolean;
  wrapExperimentNames: boolean;
};

function layoutForColumn<T>(table: TTable<T>, column: Column<T, unknown>): { className: string; style: CSSProperties } {
  const width = column.getSize();
  return { className: "", style: { width, minWidth: width, maxWidth: width } };
}

export function MetricsTableSortableRow({
  row,
  table,
  isRowSelected,
  pinLeadColumns,
  leadColumnCount,
  gripWidthPx,
  rowReorderDisabled,
  wrapExperimentNames,
}: MetricsTableSortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: row.id,
    disabled: rowReorderDisabled,
  });

  const expColor = row.original.experimentColor;
  const selectedRowStyle = isRowSelected ? getExperimentSelectionSurfaceStyle(expColor) : undefined;
  const transformStr = transform ? CSS.Transform.toString(transform) : undefined;

  const pinGrip = pinLeadColumns && leadColumnCount >= 1;
  const pinExperiment = pinLeadColumns && leadColumnCount >= 2;

  const style = {
    ...(transformStr ? { transform: transformStr } : {}),
    transition,
    opacity: isDragging ? 0.5 : 1,
    ...(selectedRowStyle ?? {}),
  };

  const gripReorderTitle = rowReorderDisabled
    ? "Clear the name filter and column sorting to reorder experiments"
    : "Reorder";

  return (
    <TableRow
      ref={setNodeRef}
      data-state={isRowSelected ? "selected" : undefined}
      className={cn("group", isRowSelected ? "transition-colors" : undefined)}
      style={style}
    >
      <TableCell
        className={cn(
          "px-2 py-2 align-middle group-hover:bg-muted/50",
          pinGrip && stickyGripCell
        )}
        style={{
          width: gripWidthPx,
          minWidth: gripWidthPx,
          maxWidth: gripWidthPx,
          ...(selectedRowStyle?.backgroundColor
            ? { backgroundColor: selectedRowStyle.backgroundColor }
            : {}),
        }}
      >
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
      </TableCell>
      {row.getVisibleCells().map((cell) => {
        const isExperiment = cell.column.id === "experiment";
        const layout = layoutForColumn(table, cell.column);
        return (
          <TableCell
            key={cell.id}
            className={cn(
              "align-top",
              isExperiment &&
                (wrapExperimentNames
                  ? "whitespace-normal break-words"
                  : "overflow-hidden whitespace-nowrap"),
              pinExperiment && isExperiment && stickyExperimentCell,
              pinExperiment && isExperiment && "group-hover:bg-muted/50",
              layout.className
            )}
            style={
              pinExperiment && isExperiment
                ? {
                    ...layout.style,
                    left: gripWidthPx,
                    ...(selectedRowStyle
                      ? {
                          ...selectedRowStyle,
                          boxShadow: `${selectedRowStyle.boxShadow}, 4px 0 12px -8px rgba(0,0,0,0.08)`,
                        }
                      : {}),
                  }
                : layout.style
            }
          >
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </TableCell>
        );
      })}
    </TableRow>
  );
}
