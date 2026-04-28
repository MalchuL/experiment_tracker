"use client";

import { flexRender, type Table as TTable } from "@tanstack/react-table";
import { ChevronDown, Download, Loader2, Table2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { downloadTableReport } from "./lib/export-report";
import type { MetricsTableRow } from "./lib/types";

type ProjectMetricsTableSectionProps = {
  dataLoading: boolean;
  isError: boolean;
  canShowTable: boolean;
  table: TTable<MetricsTableRow>;
  editMode: boolean;
  nameFilter: string;
  /** Rows after row-hide (report); used for empty + footer copy. */
  rowsInReport: MetricsTableRow[];
  filteredRows: MetricsTableRow[];
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
  latest: { total: number } | undefined;
  tableDataLength: number;
  hiddenRowIds: Set<string>;
  hiddenColumnIds: Set<string>;
  /** Highlights this row in the table while the experiment sidebar is open. */
  selectedExperimentId: string | null;
  /** Used for download filenames, e.g. project-metrics-train. */
  exportFileBase: string;
};

/** Renders the pivot table, load-more, and status line. */
export function ProjectMetricsTableSection({
  dataLoading,
  isError,
  canShowTable,
  table,
  editMode,
  nameFilter,
  rowsInReport,
  filteredRows,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  latest,
  tableDataLength,
  hiddenRowIds,
  hiddenColumnIds,
  selectedExperimentId,
  exportFileBase,
}: ProjectMetricsTableSectionProps) {
  return (
    <div className="space-y-3">
      {isError && (
        <p className="text-sm text-destructive" role="alert">
          Failed to load metrics snapshot. Check permissions and network.
        </p>
      )}

      {dataLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          Loading snapshot…
        </div>
      )}

      {canShowTable && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Table2 className="h-4 w-4" aria-hidden />
              <span>Metrics grid</span>
            </div>
            {!editMode && table.getRowModel().rows.length > 0 ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    aria-label="Download table"
                  >
                    <Download className="h-3.5 w-3.5 shrink-0" />
                    Download
                    <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onSelect={() => downloadTableReport(table, "csv", exportFileBase)}
                  >
                    Comma-separated (CSV)
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => downloadTableReport(table, "json", exportFileBase)}
                    title='JSON array: [column names, ...rows] — a "list of lists"'
                  >
                    JSON (list of rows)
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => downloadTableReport(table, "markdown", exportFileBase)}
                  >
                    Markdown table
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </div>
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table
              className="w-full"
              style={{ width: table.getTotalSize() }}
            >
            <TableHeader>
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id}>
                  {hg.headers.map((h) => (
                    <TableHead
                      key={h.id}
                      colSpan={h.colSpan}
                      className={cn(
                        "relative align-top px-4",
                        editMode ? "h-auto min-h-12" : "h-12",
                        h.column.id === "experiment" ? "text-left" : "text-right"
                      )}
                      style={{ width: h.getSize() }}
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getCanResize() && (
                        <div
                          onMouseDown={h.getResizeHandler()}
                          onTouchStart={h.getResizeHandler()}
                          className={cn(
                            "absolute right-0 top-0 h-full w-1 touch-none select-none cursor-col-resize",
                            "bg-border opacity-50 hover:opacity-100",
                            h.column.getIsResizing() && "bg-primary"
                          )}
                        />
                      )}
                    </TableHead>
                  ))}
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
                  return (
                  <TableRow
                    key={row.id}
                    data-state={isRowSelected ? "selected" : undefined}
                    className={isRowSelected ? "transition-colors" : undefined}
                    style={
                      isRowSelected
                        ? {
                            backgroundColor: `color-mix(in srgb, ${expColor} 20%, var(--background))`,
                            boxShadow: `inset 4px 0 0 0 ${expColor}`,
                          }
                        : undefined
                    }
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="align-top" style={{ width: cell.column.getSize() }}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                  );
                })
              )}
            </TableBody>
            </Table>
          </div>
        </div>
      )}

      {hasNextPage && (
        <Button variant="outline" size="sm" onClick={onLoadMore} disabled={isFetchingNextPage} type="button">
          {isFetchingNextPage ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading…
            </>
          ) : (
            "Load more experiments"
          )}
        </Button>
      )}

      {latest && (
        <p className="text-xs text-muted-foreground">
          Showing {tableDataLength} experiment{tableDataLength === 1 ? "" : "s"} in the table
          {nameFilter ? " (name filter on loaded data)" : ""}
          {editMode ? ` — report when edit is off: ${rowsInReport.length} row(s)` : null}
          {hiddenRowIds.size > 0 ? ` — ${hiddenRowIds.size} row(s) hidden in report` : ""}
          {hiddenColumnIds.size > 0 ? ` — ${hiddenColumnIds.size} column(s) hidden in report` : ""} · {latest.total}{" "}
          in project for this label
        </p>
      )}
    </div>
  );
}
