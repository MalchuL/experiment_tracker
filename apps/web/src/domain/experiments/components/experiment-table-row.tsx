"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { GripVertical } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { format, parseISO } from "date-fns";
import { Metric } from "@/domain/metrics/types";
import { displayMetricKeyEquals, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import {
  formatMetricScalarForDisplay,
  formatMetricScalarTooltipFull,
} from "@/lib/metrics/metric-value-display";
import { getExperimentSelectionSurfaceStyle } from "../experiment-selection-style";
import { ExperimentTruncatedText } from "./experiment-truncated-text";
import { cn } from "@/lib/utils";
import {
  EXPERIMENTS_TABLE_COLUMN,
  experimentsTableColumnWidthFallback,
  metricColumnId,
} from "@/domain/experiments/lib/experiments-table-column-widths";

const stickyGripCell = cn(
  "sticky left-0 z-[2] border-r border-border bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);
const stickyExperimentCell = cn(
  "sticky z-[2] border-r border-border bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);

interface ExperimentTableRowProps {
  experiment: Experiment;
  onClick: () => void;
  isSelected?: boolean;
  /** When true, row is not draggable (e.g. list is search-filtered; reorder must use full list). */
  reorderDisabled?: boolean;
  projectMetrics?: ProjectMetric[];
  expMetrics?: Metric[];
  parentName?: string;
  experimentTableResolvedColumnWidths: Record<string, number>;
  experimentTableGripColumnWidthPx: number;
}

export function ExperimentTableRow({
  experiment,
  onClick,
  isSelected,
  reorderDisabled = false,
  projectMetrics,
  expMetrics,
  parentName,
  experimentTableResolvedColumnWidths,
  experimentTableGripColumnWidthPx,
}: ExperimentTableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: experiment.id,
    disabled: reorderDisabled,
  });

  const transformStr = transform ? CSS.Transform.toString(transform) : undefined;
  const selectionSurface = isSelected ? getExperimentSelectionSurfaceStyle(experiment.color) : undefined;
  const stickyCellBackground =
    selectionSurface != null ? { backgroundColor: selectionSurface.backgroundColor } : undefined;

  const style = {
    ...(transformStr ? { transform: transformStr } : {}),
    transition,
    opacity: isDragging ? 0.5 : 1,
    ...(selectionSurface ?? {}),
  };

  const getExperimentTableColumnWidth = (columnId: string) =>
    experimentTableResolvedColumnWidths[columnId] ?? experimentsTableColumnWidthFallback(columnId);

  const experimentNameColumnWidthPx = getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.experiment);
  const statusColumnWidthPx = getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.status);
  const parentNameColumnWidthPx = getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.parent);
  const createdAtColumnWidthPx = getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.created);

  return (
    <TableRow
      ref={setNodeRef}
      data-state={isSelected ? "selected" : undefined}
      style={style}
      className={
        isSelected
          ? "cursor-pointer transition-colors hover-elevate"
          : "cursor-pointer hover-elevate"
      }
      onClick={onClick}
      data-testid={`row-experiment-${experiment.id}`}
    >
      <TableCell
        className={cn("px-2", stickyGripCell)}
        style={{
          width: experimentTableGripColumnWidthPx,
          minWidth: experimentTableGripColumnWidthPx,
          maxWidth: experimentTableGripColumnWidthPx,
          ...stickyCellBackground,
        }}
      >
        <div
          className={
            reorderDisabled
              ? "cursor-not-allowed p-1 opacity-40"
              : "cursor-grab p-1 active:cursor-grabbing"
          }
          title={reorderDisabled ? "Clear the search filter to reorder experiments" : undefined}
          {...attributes}
          {...(reorderDisabled ? {} : listeners)}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </div>
      </TableCell>
      <TableCell
        className={cn("overflow-hidden px-4 align-middle", stickyExperimentCell)}
        style={{
          width: experimentNameColumnWidthPx,
          minWidth: experimentNameColumnWidthPx,
          maxWidth: experimentNameColumnWidthPx,
          left: experimentTableGripColumnWidthPx,
          ...stickyCellBackground,
        }}
      >
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: experiment.color }}
          />
          <div className="min-w-0 flex-1">
            <ExperimentTruncatedText
              variant="table"
              text={experiment.name}
              className="font-medium"
            />
            {experiment.description ? (
              <ExperimentTruncatedText
                variant="table"
                tableClamp="multi"
                text={experiment.description}
                className="mt-0.5 text-xs text-muted-foreground"
              />
            ) : null}
          </div>
        </div>
      </TableCell>
      <TableCell
        className="overflow-hidden whitespace-nowrap"
        style={{ width: statusColumnWidthPx, minWidth: statusColumnWidthPx, maxWidth: statusColumnWidthPx }}
      >
        <StatusBadge status={experiment.status} />
      </TableCell>
      <TableCell
        className="min-w-0 overflow-hidden text-sm text-muted-foreground"
        style={{
          width: parentNameColumnWidthPx,
          minWidth: parentNameColumnWidthPx,
          maxWidth: parentNameColumnWidthPx,
        }}
      >
        {parentName ? (
          <div className="min-w-0 max-w-full">
            <ExperimentTruncatedText
              variant="table"
              text={parentName}
              as="span"
              className="block"
            />
          </div>
        ) : (
          "-"
        )}
      </TableCell>
      {projectMetrics?.map((metric) => {
        const raw = expMetrics?.find((m) =>
          displayMetricKeyEquals(
            { name: m.name, label: m.label },
            { name: metric.name, label: metric.label ?? null }
          )
        )?.value;
        const metricColumnIdValue = metricColumnId(metric);
        const metricColumnWidthPx = getExperimentTableColumnWidth(metricColumnIdValue);
        return (
          <TableCell
            key={projectMetricKeyString(metric)}
            className="overflow-hidden whitespace-nowrap text-right font-mono text-sm"
            style={{ width: metricColumnWidthPx, minWidth: metricColumnWidthPx, maxWidth: metricColumnWidthPx }}
          >
            <span
              className="inline-block min-w-0 max-w-full cursor-default text-right tabular-nums"
              title={formatMetricScalarTooltipFull(raw)}
            >
              {formatMetricScalarForDisplay(raw)}
            </span>
          </TableCell>
        );
      })}
      <TableCell
        className="overflow-hidden whitespace-nowrap text-sm text-muted-foreground tabular-nums"
        style={{ width: createdAtColumnWidthPx, minWidth: createdAtColumnWidthPx, maxWidth: createdAtColumnWidthPx }}
        title={format(parseISO(experiment.createdAt), "MMM d, yyyy, HH:mm")}
      >
        <span className="block min-w-0 truncate">
          {format(parseISO(experiment.createdAt), "MMM d, yyyy, HH:mm")}
        </span>
      </TableCell>
    </TableRow>
  );
}
