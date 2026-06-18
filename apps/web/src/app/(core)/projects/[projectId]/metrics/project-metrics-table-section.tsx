"use client";

import type { CSSProperties } from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { flexRender, type Column, type Table as TTable } from "@tanstack/react-table";
import { Loader2 } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { EXPERIMENTS_TABLE_GRIP_PX } from "@/domain/experiments/lib/experiments-table-column-widths";
import { SHOW_IN_REPORT_COLUMN_ID, SHOW_IN_REPORT_COLUMN_PX, METRICS_TABLE_ROW_BORDER_CLASS } from "./lib/constants";
import { reorderIdSubset } from "./lib/row-order";
import type { MetricsTableRow } from "./lib/types";
import { MetricsTableSortableRow } from "./components/metrics-table-sortable-row";

const stickyGripTh = cn(
  "sticky left-0 z-[21] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);
const stickyExperimentTh = cn(
  "sticky z-[21] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border"
);
const stickyShowInReportTh = cn(
  "sticky z-[21] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border"
);
const headerSeparatorClass =
  "after:absolute after:right-0 after:top-2 after:bottom-2 after:w-px after:bg-border after:content-['']";

function layoutForColumn<T>(
  table: TTable<T>,
  column: Column<T, unknown>
): { className: string; style: CSSProperties } {
  const width = column.getSize();
  return { className: "", style: { width, minWidth: width, maxWidth: width } };
}

type ProjectMetricsTableSectionProps = {
  dataLoading: boolean;
  isError: boolean;
  canShowTable: boolean;
  table: TTable<MetricsTableRow>;
  editMode: boolean;
  /** Rows after row-hide (report); used for empty state copy. */
  rowsInReport: MetricsTableRow[];
  filteredRows: MetricsTableRow[];
  /** Highlights this row in the table while the experiment sidebar is open. */
  selectedExperimentId: string | null;
  wrapExperimentNames: boolean;
  wrapValues: boolean;
  rowReorderDisabled: boolean;
  experimentRowOrder: string[];
  onExperimentRowReorder: (orderedIds: string[]) => void;
  tableData: MetricsTableRow[];
};

/** Pivot table body: scrolls inside `ProjectDataTableFrame` (toolbar/footer live on the page). */
export function ProjectMetricsTableSection({
  dataLoading,
  isError,
  canShowTable,
  table,
  editMode,
  rowsInReport,
  filteredRows,
  selectedExperimentId,
  wrapExperimentNames,
  wrapValues,
  rowReorderDisabled,
  experimentRowOrder,
  onExperimentRowReorder,
  tableData,
}: ProjectMetricsTableSectionProps) {
  const { pinLeadColumns, leadColumnCount } = useProjectDataTableFrame();
  const gripWidthPx = EXPERIMENTS_TABLE_GRIP_PX;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const pinGrip = pinLeadColumns && leadColumnCount >= 1;
  const pinShowInReport = pinLeadColumns && leadColumnCount >= 2 && editMode;
  const pinExperiment = pinLeadColumns && leadColumnCount >= (editMode ? 3 : 2);
  const showInReportWidth = editMode
    ? (table.getColumn(SHOW_IN_REPORT_COLUMN_ID)?.getSize() ?? SHOW_IN_REPORT_COLUMN_PX)
    : 0;
  const experimentStickyLeft = gripWidthPx + (editMode ? showInReportWidth : 0);

  const rowIds = table.getRowModel().rows.map((r) => r.id);

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    if (rowReorderDisabled || !over || active.id === over.id) return;
    const subsetIds = tableData.map((r) => r.experimentId);
    onExperimentRowReorder(
      reorderIdSubset(experimentRowOrder, subsetIds, String(active.id), String(over.id))
    );
  };

  const gripReorderTitle = rowReorderDisabled
    ? "Clear the name filter and column sorting to reorder experiments"
    : "Reorder";

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
      {isError && (
        <p className="shrink-0 text-sm text-destructive" role="alert">
          Failed to load metrics snapshot. Check permissions and network.
        </p>
      )}

      {dataLoading && (
        <div className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          Loading snapshot…
        </div>
      )}

      {canShowTable && (
        <div className="min-h-0 min-w-0 flex-1">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <Table
              containerClassName="overflow-visible w-full min-w-0"
              className="table-fixed border-separate border-spacing-0"
              style={{ width: table.getTotalSize() + gripWidthPx }}
            >
              <TableHeader className="sticky top-0 z-20 bg-background shadow-[0_1px_0_0_hsl(var(--border))]">
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id} className="hover:bg-transparent">
                    <TableHead
                      className={cn(
                        "relative h-12 px-2 text-left align-middle font-medium text-muted-foreground",
                        METRICS_TABLE_ROW_BORDER_CLASS,
                        pinGrip && stickyGripTh,
                        headerSeparatorClass
                      )}
                      style={{
                        width: gripWidthPx,
                        minWidth: gripWidthPx,
                        maxWidth: gripWidthPx,
                      }}
                      aria-label="Reorder"
                      title={gripReorderTitle}
                    />
                    {hg.headers.map((h) => {
                      const isExperiment = h.column.id === "experiment";
                      const isShowInReport = h.column.id === SHOW_IN_REPORT_COLUMN_ID;
                      const layout = layoutForColumn(table, h.column);
                      return (
                        <TableHead
                          key={h.id}
                          colSpan={h.colSpan}
                          aria-label={isShowInReport ? "Show in report" : undefined}
                          className={cn(
                            "relative align-top",
                            METRICS_TABLE_ROW_BORDER_CLASS,
                            isShowInReport ? "px-1" : "px-4",
                            editMode ? "h-auto min-h-12" : "h-12",
                            !isExperiment && !isShowInReport && !editMode && "overflow-hidden",
                            isExperiment || isShowInReport ? "text-left" : "text-right",
                            pinShowInReport && isShowInReport && stickyShowInReportTh,
                            pinExperiment && isExperiment && stickyExperimentTh,
                            (isExperiment || isShowInReport) && headerSeparatorClass,
                            layout.className
                          )}
                          style={
                            pinShowInReport && isShowInReport
                              ? { ...layout.style, left: gripWidthPx }
                              : pinExperiment && isExperiment
                                ? { ...layout.style, left: experimentStickyLeft }
                                : layout.style
                          }
                        >
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {h.column.getCanResize() && (
                            <div
                              onMouseDown={h.getResizeHandler()}
                              onTouchStart={h.getResizeHandler()}
                              className={cn(
                                "absolute right-0 top-0 z-10 flex h-full w-2.5 cursor-col-resize items-center justify-center",
                                "touch-none select-none"
                              )}
                            >
                              {isExperiment ? null : (
                                <span
                                  aria-hidden
                                  className={cn(
                                    "block h-[calc(100%-1rem)] w-px shrink-0 self-center bg-border transition-colors",
                                    "hover:bg-muted-foreground/70",
                                    h.column.getIsResizing() && "bg-primary"
                                  )}
                                />
                              )}
                            </div>
                          )}
                        </TableHead>
                      );
                    })}
                  </TableRow>
                ))}
              </TableHeader>
              <SortableContext items={rowIds} strategy={verticalListSortingStrategy}>
                <TableBody className="[&_tr:last-child_td]:border-b-0">
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={Math.max(1, table.getVisibleLeafColumns().length + 1)}
                        className={cn(
                          "text-center text-sm text-muted-foreground",
                          METRICS_TABLE_ROW_BORDER_CLASS
                        )}
                      >
                        {rowsInReport.length === 0 && filteredRows.length > 0
                          ? "All matching experiments are hidden. Turn on Edit mode to re-enable rows with checkboxes."
                          : "No rows on this page. Try a different label or “include experiments without metrics”."}
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <MetricsTableSortableRow
                        key={row.id}
                        row={row}
                        table={table}
                        isRowSelected={selectedExperimentId === row.original.experimentId}
                        pinLeadColumns={pinLeadColumns}
                        leadColumnCount={leadColumnCount}
                        gripWidthPx={gripWidthPx}
                        rowReorderDisabled={rowReorderDisabled}
                        editMode={editMode}
                        wrapExperimentNames={wrapExperimentNames}
                        wrapValues={wrapValues}
                      />
                    ))
                  )}
                </TableBody>
              </SortableContext>
            </Table>
          </DndContext>
        </div>
      )}
    </div>
  );
}
