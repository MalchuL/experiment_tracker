"use client";

import type { CSSProperties } from "react";
import { flexRender, type Column, type Table as TTable } from "@tanstack/react-table";
import { Loader2 } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { getExperimentSelectionSurfaceStyle } from "@/domain/experiments/experiment-selection-style";
import type { MetricsTableRow } from "./lib/types";

const stickyExperimentTh = cn(
  "sticky left-0 z-[21] border-r border-border bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border"
);

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
}: ProjectMetricsTableSectionProps) {
  const { pinLeadColumns, leadColumnCount } = useProjectDataTableFrame();

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
          <Table
            containerClassName="overflow-visible w-full min-w-0"
            className="table-fixed border-separate border-spacing-0"
            style={{ width: table.getTotalSize() }}
          >
            <TableHeader className="sticky top-0 z-20 bg-background shadow-[0_1px_0_0_hsl(var(--border))]">
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id}>
                  {hg.headers.map((h) => {
                    const pinExperiment =
                      pinLeadColumns && leadColumnCount >= 1 && h.column.id === "experiment";
                    const layout = layoutForColumn(table, h.column);
                    return (
                      <TableHead
                        key={h.id}
                        colSpan={h.colSpan}
                        className={cn(
                          "relative align-top px-4",
                          editMode ? "h-auto min-h-12" : "h-12",
                          h.column.id === "experiment" ? "text-left" : "text-right",
                          pinExperiment && stickyExperimentTh,
                          layout.className
                        )}
                        style={layout.style}
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
                            <span
                              aria-hidden
                              className={cn(
                                "block h-full w-px shrink-0 bg-border transition-colors",
                                "hover:bg-muted-foreground/70",
                                h.column.getIsResizing() && "bg-primary"
                              )}
                            />
                          </div>
                        )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={Math.max(1, table.getVisibleLeafColumns().length)}
                    className="text-center text-sm text-muted-foreground"
                  >
                    {rowsInReport.length === 0 && filteredRows.length > 0
                      ? "All matching experiments are hidden. Turn on Edit mode to re-enable rows with checkboxes."
                      : "No rows on this page. Try a different label or “include experiments without metrics”."}
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => {
                  const isRowSelected = selectedExperimentId === row.original.experimentId;
                  const expColor = row.original.experimentColor;
                  const selectedRowStyle = isRowSelected
                    ? getExperimentSelectionSurfaceStyle(expColor)
                    : undefined;
                  return (
                    <TableRow
                      key={row.id}
                      data-state={isRowSelected ? "selected" : undefined}
                      className={cn("group", isRowSelected ? "transition-colors" : undefined)}
                      style={selectedRowStyle}
                    >
                      {row.getVisibleCells().map((cell) => {
                        const pinExperiment =
                          pinLeadColumns &&
                          leadColumnCount >= 1 &&
                          cell.column.id === "experiment";
                        const layout = layoutForColumn(table, cell.column);
                        return (
                          <TableCell
                            key={cell.id}
                            className={cn(
                              "align-top",
                              pinExperiment && stickyExperimentTh,
                              pinExperiment && "group-hover:bg-muted/50",
                              layout.className
                            )}
                            style={
                              pinExperiment && selectedRowStyle
                                ? {
                                    ...layout.style,
                                    ...selectedRowStyle,
                                    boxShadow: `${selectedRowStyle.boxShadow}, 4px 0 12px -8px rgba(0,0,0,0.08)`,
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
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
