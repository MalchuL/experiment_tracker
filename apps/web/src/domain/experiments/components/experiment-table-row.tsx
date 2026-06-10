"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { GripVertical, Medal } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { format, parseISO } from "date-fns";
import { Metric, TopMetric } from "@/domain/metrics/types";
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
import { findTopMetric } from "../lib/selective-metrics";
import { ExperimentSelectionOrderBadge } from "./experiment-selection-order-badge";

const stickyGripCell = cn(
  "sticky left-0 z-[2] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);
const stickyExperimentCell = cn(
  "sticky z-[2] bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);

const rowSeparatorClass = "border-y border-border/70";
/** Fixed lead-column control slot — grip icon and selection badge share the same footprint. */
const GRIP_LEAD_SLOT_CLASS = "flex h-6 w-6 shrink-0 items-center justify-center";

interface ExperimentTableRowProps {
  experiment: Experiment;
  onClick: () => void;
  isSelected?: boolean;
  /** When true, row is not draggable (e.g. list is search-filtered; reorder must use full list). */
  reorderDisabled?: boolean;
  projectMetrics?: ProjectMetric[];
  expMetrics?: Metric[];
  topMetrics?: TopMetric[];
  parentName?: string;
  experimentTableResolvedColumnWidths: Record<string, number>;
  experimentTableGripColumnWidthPx: number;
  pinStickyLead?: boolean;
  selectionMode?: boolean;
  selectionOrderNumber?: number | null;
  onSelectionToggle?: () => void;
}

export function ExperimentTableRow({
  experiment,
  onClick,
  isSelected,
  reorderDisabled = false,
  projectMetrics,
  expMetrics,
  topMetrics,
  parentName,
  experimentTableResolvedColumnWidths,
  experimentTableGripColumnWidthPx,
  pinStickyLead = true,
  selectionMode = false,
  selectionOrderNumber = null,
  onSelectionToggle,
}: ExperimentTableRowProps) {
  const dragDisabled = reorderDisabled || selectionMode;
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: experiment.id,
    disabled: dragDisabled,
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

  const gripCellClass = pinStickyLead ? stickyGripCell : "bg-background box-border overflow-hidden";
  const experimentCellClass = pinStickyLead
    ? stickyExperimentCell
    : "bg-background box-border overflow-hidden";

  return (
    <TableRow
      ref={setNodeRef}
      data-state={isSelected ? "selected" : undefined}
      style={style}
      className={cn(
        "group cursor-pointer hover-elevate",
        isSelected && "transition-colors"
      )}
      onClick={onClick}
      data-testid={`row-experiment-${experiment.id}`}
    >
      <TableCell
        className={cn(
          "px-2 py-2 align-middle group-hover:bg-muted/50",
          rowSeparatorClass,
          gripCellClass
        )}
        style={{
          width: experimentTableGripColumnWidthPx,
          minWidth: experimentTableGripColumnWidthPx,
          maxWidth: experimentTableGripColumnWidthPx,
          ...stickyCellBackground,
        }}
      >
        {selectionMode && onSelectionToggle ? (
          <div className={GRIP_LEAD_SLOT_CLASS} onClick={(e) => e.stopPropagation()}>
            <ExperimentSelectionOrderBadge
              experimentId={experiment.id}
              experimentName={experiment.name}
              orderNumber={selectionOrderNumber}
              onToggle={onSelectionToggle}
            />
          </div>
        ) : (
          <div
            className={cn(
              GRIP_LEAD_SLOT_CLASS,
              dragDisabled
                ? "cursor-not-allowed opacity-40"
                : "cursor-grab active:cursor-grabbing"
            )}
            title={
              reorderDisabled ? "Clear the search filter to reorder experiments" : undefined
            }
            {...attributes}
            {...(dragDisabled ? {} : listeners)}
            onClick={(e) => e.stopPropagation()}
          >
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
      </TableCell>
      <TableCell
        className={cn(
          "overflow-hidden px-4 align-middle group-hover:bg-muted/50",
          rowSeparatorClass,
          experimentCellClass
        )}
        style={{
          width: experimentNameColumnWidthPx,
          minWidth: experimentNameColumnWidthPx,
          maxWidth: experimentNameColumnWidthPx,
          ...(pinStickyLead ? { left: experimentTableGripColumnWidthPx } : {}),
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
        className={cn("overflow-hidden whitespace-nowrap", rowSeparatorClass)}
        style={{ width: statusColumnWidthPx, minWidth: statusColumnWidthPx, maxWidth: statusColumnWidthPx }}
      >
        <StatusBadge status={experiment.status} />
      </TableCell>
      <TableCell
        className={cn("min-w-0 overflow-hidden text-sm text-muted-foreground", rowSeparatorClass)}
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
        const topMetric = findTopMetric(topMetrics, experiment.id, metric);
        const medalClass =
          topMetric?.position === 1
            ? "text-amber-500"
            : topMetric?.position === 2
              ? "text-slate-400"
              : "text-orange-700";
        return (
          <TableCell
            key={projectMetricKeyString(metric)}
            className={cn("overflow-hidden whitespace-nowrap text-right font-mono text-sm", rowSeparatorClass)}
            style={{ width: metricColumnWidthPx, minWidth: metricColumnWidthPx, maxWidth: metricColumnWidthPx }}
          >
            <span
              className="inline-flex min-w-0 max-w-full items-center justify-end gap-1.5 cursor-default text-right tabular-nums"
              title={formatMetricScalarTooltipFull(raw)}
            >
              {topMetric ? (
                <Medal
                  className={cn("h-4 w-4 shrink-0", medalClass)}
                  aria-label={`Project rank ${topMetric.position}`}
                />
              ) : null}
              {formatMetricScalarForDisplay(raw)}
            </span>
          </TableCell>
        );
      })}
      <TableCell
        className={cn(
          "overflow-hidden whitespace-nowrap text-sm text-muted-foreground tabular-nums",
          rowSeparatorClass
        )}
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
