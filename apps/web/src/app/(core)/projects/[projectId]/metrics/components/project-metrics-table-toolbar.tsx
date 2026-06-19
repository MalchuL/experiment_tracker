"use client";

import { ChevronDown, Download, PanelLeft, PanelLeftClose, Table2 } from "lucide-react";
import type { Table as TTable } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { downloadTableReport } from "../lib/export-report";
import type { MetricsTableRow } from "../lib/types";

type ProjectMetricsTableToolbarProps = {
  table: TTable<MetricsTableRow>;
  exportFileBase: string;
  showDownload: boolean;
  controlsOpen: boolean;
  onControlsOpenChange: (open: boolean) => void;
};

export function ProjectMetricsTableToolbar({
  table,
  exportFileBase,
  showDownload,
  controlsOpen,
  onControlsOpenChange,
}: ProjectMetricsTableToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <Table2 className="h-4 w-4 shrink-0" aria-hidden />
        <span>Metrics grid</span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          aria-label={controlsOpen ? "Hide controls" : "Show controls"}
          aria-expanded={controlsOpen}
          onClick={() => onControlsOpenChange(!controlsOpen)}
        >
          {controlsOpen ? (
            <PanelLeftClose className="h-3.5 w-3.5 shrink-0" aria-hidden />
          ) : (
            <PanelLeft className="h-3.5 w-3.5 shrink-0" aria-hidden />
          )}
          Controls
        </Button>
        {showDownload ? (
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
              <DropdownMenuItem onSelect={() => downloadTableReport(table, "csv", exportFileBase)}>
                Comma-separated (CSV)
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() => downloadTableReport(table, "json", exportFileBase)}
                title='JSON array: [column names, ...rows] — a "list of lists"'
              >
                JSON (list of rows)
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => downloadTableReport(table, "markdown", exportFileBase)}>
                Markdown table
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
    </div>
  );
}
