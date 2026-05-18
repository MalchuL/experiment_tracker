"use client";

import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Experiment } from "../types";
import { ProjectMetric } from "@/domain/projects/types";
import { ExperimentTableRow } from "./experiment-table-row";
import { arrayMove } from "@dnd-kit/sortable";
import { Metric } from "@/domain/metrics/types";
import { formatMetricLabel } from "@/lib/metrics/format-metric-label";
import { cn } from "@/lib/utils";
import { useProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { useExperimentsTableColumnWidths } from "@/domain/experiments/hooks/use-experiments-table-column-widths";
import {
  EXPERIMENTS_TABLE_COLUMN,
  experimentsTableColumnWidthFallback,
  metricColumnId,
} from "@/domain/experiments/lib/experiments-table-column-widths";

const stickyGripTh = cn(
  "sticky z-[21] border-r border-border bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden",
  "left-0"
);

const stickyExperimentTh = cn(
  "sticky z-[21] border-r border-border bg-background shadow-[4px_0_12px_-8px_rgba(0,0,0,0.08)] box-border overflow-hidden"
);

function HeaderResizeHandle({
  columnId,
  onBeginResize,
}: {
  columnId: string;
  onBeginResize: (columnId: string, clientX: number) => void;
}) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={`Resize ${columnId} column`}
      onMouseDown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onBeginResize(columnId, e.clientX);
      }}
      onTouchStart={(e) => {
        e.preventDefault();
        e.stopPropagation();
        const t = e.touches[0];
        if (t) onBeginResize(columnId, t.clientX);
      }}
      className={cn(
        "absolute right-0 top-0 z-10 flex h-full w-2.5 cursor-col-resize items-center justify-center",
        "touch-none select-none"
      )}
    >
      <span
        aria-hidden
        className="block h-full w-px shrink-0 bg-border transition-colors hover:bg-muted-foreground/70"
      />
    </div>
  );
}

interface ExperimentsTableProps {
  /** Used to persist column widths per project. */
  projectId: string | undefined;
  experiments: Experiment[];
  /** When true, drag-to-reorder is disabled (e.g. while the list is filtered by search). */
  reorderDisabled?: boolean;
  projectMetrics?: ProjectMetric[];
  aggregatedMetrics?: Record<string, Metric[]>;
  /** Parent names for ids not present in the loaded experiment pages (batch-fetched). */
  parentNamesById?: Record<string, string>;
  /** Names for all experiments currently in the infinite-query cache (for parent column when rows are filtered). */
  loadedExperimentNameById?: Record<string, string>;
  selectedExperimentId?: string | null;
  onExperimentClick: (experimentId: string) => void;
  onReorder: (experimentIds: string[]) => void;
}

export function ExperimentsTable({
  projectId,
  experiments,
  reorderDisabled = false,
  projectMetrics,
  aggregatedMetrics,
  parentNamesById,
  loadedExperimentNameById,
  selectedExperimentId,
  onExperimentClick,
  onReorder,
}: ExperimentsTableProps) {
  const { pinLeadColumns, leadColumnCount } = useProjectDataTableFrame();
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const filteredMetrics = projectMetrics || [];
  const {
    experimentTableResolvedColumnWidths,
    startResize,
    experimentTableTotalWidthPx,
  } = useExperimentsTableColumnWidths(projectId, filteredMetrics, {
    experiments,
    aggregatedMetrics,
  });

  const getExperimentTableColumnWidth = (columnId: string) =>
    experimentTableResolvedColumnWidths[columnId] ?? experimentsTableColumnWidthFallback(columnId);

  const handleDragEnd = (event: DragEndEvent) => {
    if (reorderDisabled) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = experiments.findIndex((e) => e.id === active.id);
    const newIndex = experiments.findIndex((e) => e.id === over.id);

    const newOrder = arrayMove(experiments, oldIndex, newIndex);
    onReorder(newOrder.map((e) => e.id));
  };

  const experimentTableGripColumnWidthPxResolved = getExperimentTableColumnWidth(
    EXPERIMENTS_TABLE_COLUMN.grip
  );
  const experimentNameColumnWidthPx = getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.experiment);

  const pinSticky = pinLeadColumns && leadColumnCount >= 2;
  const gripThClass = pinSticky ? stickyGripTh : "border-r border-border bg-background box-border overflow-hidden";
  const experimentThClass = pinSticky
    ? stickyExperimentTh
    : "relative border-r border-border bg-background box-border overflow-hidden";

  return (
    <Card className="min-w-0 shrink-0 border-0 bg-transparent shadow-none">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <Table
          containerClassName="overflow-visible w-full min-w-0"
          className="table-fixed border-separate border-spacing-0"
          style={{ width: experimentTableTotalWidthPx }}
        >
          <TableHeader className="sticky top-0 z-20 bg-background shadow-[0_1px_0_0_hsl(var(--border))]">
            <TableRow>
              <TableHead
                className={cn(
                  "h-12 px-2 text-left align-middle font-medium text-muted-foreground",
                  gripThClass
                )}
                style={{
                  width: experimentTableGripColumnWidthPxResolved,
                  minWidth: experimentTableGripColumnWidthPxResolved,
                  maxWidth: experimentTableGripColumnWidthPxResolved,
                }}
                aria-label="Reorder"
                title={
                  reorderDisabled ? "Clear the search filter to reorder experiments" : "Reorder"
                }
              />
              <TableHead
                className={cn(
                  "relative h-12 overflow-hidden px-4 text-left align-middle font-medium text-muted-foreground",
                  experimentThClass
                )}
                style={{
                  width: experimentNameColumnWidthPx,
                  minWidth: experimentNameColumnWidthPx,
                  maxWidth: experimentNameColumnWidthPx,
                  ...(pinSticky ? { left: experimentTableGripColumnWidthPxResolved } : {}),
                }}
                title="Experiment"
              >
                Experiment
                <HeaderResizeHandle
                  columnId={EXPERIMENTS_TABLE_COLUMN.experiment}
                  onBeginResize={startResize}
                />
              </TableHead>
              <TableHead
                className="relative h-12 overflow-hidden px-4 text-left align-middle font-medium text-muted-foreground"
                style={{
                  width: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.status),
                  minWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.status),
                  maxWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.status),
                }}
                title="Status"
              >
                Status
                <HeaderResizeHandle
                  columnId={EXPERIMENTS_TABLE_COLUMN.status}
                  onBeginResize={startResize}
                />
              </TableHead>
              <TableHead
                className="relative h-12 min-w-0 overflow-hidden px-4 text-left align-middle font-medium text-muted-foreground"
                style={{
                  width: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.parent),
                  minWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.parent),
                  maxWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.parent),
                }}
                title="Parent"
              >
                Parent
                <HeaderResizeHandle
                  columnId={EXPERIMENTS_TABLE_COLUMN.parent}
                  onBeginResize={startResize}
                />
              </TableHead>
              {filteredMetrics.map((metric) => {
                const metricColumnIdValue = metricColumnId(metric);
                const metricColumnWidthPx = getExperimentTableColumnWidth(metricColumnIdValue);
                const metricHeaderFullLabel = formatMetricLabel(metric.name, metric.label ?? null);
                return (
                  <TableHead
                    key={metricColumnIdValue}
                    className="relative h-12 overflow-hidden px-4 text-right align-middle font-medium text-muted-foreground"
                    style={{
                      width: metricColumnWidthPx,
                      minWidth: metricColumnWidthPx,
                      maxWidth: metricColumnWidthPx,
                    }}
                    title={metricHeaderFullLabel}
                  >
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <span className="min-w-0 truncate" title={metricHeaderFullLabel}>
                        {metricHeaderFullLabel}
                      </span>
                      {metric.direction === "minimize" ? (
                        <TrendingDown className="h-3 w-3 shrink-0" />
                      ) : (
                        <TrendingUp className="h-3 w-3 shrink-0" />
                      )}
                    </div>
                    <HeaderResizeHandle columnId={metricColumnIdValue} onBeginResize={startResize} />
                  </TableHead>
                );
              })}
              <TableHead
                className="relative h-12 overflow-hidden px-4 text-left align-middle font-medium text-muted-foreground"
                style={{
                  width: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.created),
                  minWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.created),
                  maxWidth: getExperimentTableColumnWidth(EXPERIMENTS_TABLE_COLUMN.created),
                }}
                title="Created"
              >
                Created
                <HeaderResizeHandle
                  columnId={EXPERIMENTS_TABLE_COLUMN.created}
                  onBeginResize={startResize}
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <SortableContext
            items={experiments.map((e) => e.id)}
            strategy={verticalListSortingStrategy}
          >
            <TableBody>
              {experiments.map((experiment) => {
                const pid = experiment.parentExperimentId;
                const parentInTable = experiments.find((e) => e.id === pid);
                const parentName =
                  parentInTable?.name ??
                  (pid && loadedExperimentNameById ? loadedExperimentNameById[pid] : undefined) ??
                  (pid ? parentNamesById?.[pid] : undefined);
                return (
                  <ExperimentTableRow
                    key={experiment.id}
                    experiment={experiment}
                    isSelected={selectedExperimentId === experiment.id}
                    reorderDisabled={reorderDisabled}
                    onClick={() => onExperimentClick(experiment.id)}
                    projectMetrics={filteredMetrics}
                    expMetrics={aggregatedMetrics?.[experiment.id]}
                    parentName={parentName}
                    experimentTableResolvedColumnWidths={experimentTableResolvedColumnWidths}
                    experimentTableGripColumnWidthPx={experimentTableGripColumnWidthPxResolved}
                    pinStickyLead={pinSticky}
                  />
                );
              })}
            </TableBody>
          </SortableContext>
        </Table>
      </DndContext>
    </Card>
  );
}
