"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { type Project, type ProjectDisplayMetric, type ProjectMetric } from "../../types";
import { Eye, ChevronDown, Check, TrendingUp, TrendingDown, GripVertical } from "lucide-react";
import {
  formatMetricLabel,
  isExplicitlyInDisplayList,
  normalizeDisplayMetric,
  removeFromDisplayList,
  projectMetricKeyString,
  trackedToDisplayKey,
} from "@/lib/metrics/format-metric-label";

function sortableIdForDisplayMetric(d: ProjectDisplayMetric): string {
  const n = normalizeDisplayMetric(d);
  return projectMetricKeyString(n);
}

function findTrackedForDisplay(
  tracked: ProjectMetric[],
  entry: ProjectDisplayMetric
): ProjectMetric | undefined {
  const n = normalizeDisplayMetric(entry);
  return tracked.find(
    (m) => m.name === n.name && (m.label ?? null) === (n.label ?? null)
  );
}

function SortableDisplayMetricRow({
  entry,
  trackedMetrics,
  disabled,
}: {
  entry: ProjectDisplayMetric;
  trackedMetrics: ProjectMetric[];
  disabled: boolean;
}) {
  const id = sortableIdForDisplayMetric(entry);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled,
  });
  const tracked = findTrackedForDisplay(trackedMetrics, entry);
  const label =
    typeof entry === "string" ? entry : formatMetricLabel(entry.name, entry.label ?? null);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 px-3 py-2 text-sm"
      data-testid={`display-metric-row-${id.replace(/[^a-zA-Z0-9-_]/g, "-")}`}
    >
      <button
        type="button"
        className="cursor-grab touch-none rounded-md p-1 text-muted-foreground hover:bg-muted active:cursor-grabbing disabled:pointer-events-none disabled:opacity-40"
        {...attributes}
        {...listeners}
        disabled={disabled}
        aria-label={`Reorder ${label}`}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <span className="min-w-0 flex-1 truncate font-medium">{label}</span>
      {tracked ? (
        tracked.direction === "maximize" ? (
          <TrendingUp className="h-3 w-3 shrink-0 text-green-500" />
        ) : (
          <TrendingDown className="h-3 w-3 shrink-0 text-green-500" />
        )
      ) : null}
    </div>
  );
}

interface DisplayMetricsFormProps {
  project: Project;
  onDisplayMetricsChange: (displayMetrics: ProjectDisplayMetric[]) => void | Promise<void>;
  isPending: boolean;
}

export function DisplayMetricsForm({
  project,
  onDisplayMetricsChange,
  isPending,
}: DisplayMetricsFormProps) {
  const persistedDisplayMetrics = useMemo(
    () => project.metrics.displayMetrics,
    [project.metrics]
  );

  const [displayMetrics, setDisplayMetrics] = useState<ProjectDisplayMetric[]>(persistedDisplayMetrics);

  useEffect(() => {
    setDisplayMetrics(persistedDisplayMetrics);
  }, [persistedDisplayMetrics]);

  const persist = useCallback(
    (next: ProjectDisplayMetric[]) => {
      setDisplayMetrics(next);
      void onDisplayMetricsChange(next);
    },
    [onDisplayMetricsChange]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const items = displayMetrics.map(sortableIdForDisplayMetric);
    const oldIndex = items.indexOf(String(active.id));
    const newIndex = items.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    persist(arrayMove(displayMetrics, oldIndex, newIndex));
  };

  if (project.metrics.trackedMetrics.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No metrics configured. Add metrics below first.
      </p>
    );
  }

  const sortableIds = displayMetrics.map(sortableIdForDisplayMetric);

  return (
    <div className="space-y-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-full justify-between" data-testid="dropdown-display-metrics" disabled={isPending}>
            <span className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              {displayMetrics.length === 0
                ? `0 of ${project.metrics.trackedMetrics.length} metrics selected`
                : displayMetrics.length === project.metrics.trackedMetrics.length
                  ? "All metrics selected"
                  : `${displayMetrics.length} of ${project.metrics.trackedMetrics.length} metrics selected`}
            </span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-64">
          <DropdownMenuItem
            onClick={() => {
              persist(project.metrics.trackedMetrics.map(trackedToDisplayKey));
            }}
            data-testid="menu-select-all-metrics"
          >
            <Check className="h-4 w-4 mr-2" />
            Select All
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              persist([]);
            }}
            data-testid="menu-clear-all-metrics"
          >
            Clear All
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          {project.metrics.trackedMetrics.map((metric) => {
            const checked = isExplicitlyInDisplayList(
              { name: metric.name, label: metric.label },
              displayMetrics
            );
            return (
              <DropdownMenuCheckboxItem
                key={projectMetricKeyString(metric)}
                checked={checked}
                onCheckedChange={(next) => {
                  if (next) {
                    const key = trackedToDisplayKey(metric);
                    if (!isExplicitlyInDisplayList({ name: metric.name, label: metric.label }, displayMetrics)) {
                      persist([...displayMetrics, key]);
                    }
                  } else {
                    persist(removeFromDisplayList(displayMetrics, metric));
                  }
                }}
                data-testid={`menu-metric-${projectMetricKeyString(metric).replace(/[^a-zA-Z0-9-_]/g, "-")}`}
              >
                <span className="flex items-center gap-2">
                  {formatMetricLabel(metric.name, metric.label ?? null)}
                  {metric.direction === "maximize" ? (
                    <TrendingUp className="h-3 w-3 text-green-500" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-green-500" />
                  )}
                </span>
              </DropdownMenuCheckboxItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {displayMetrics.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Drag rows to set the column order on Experiments, Kanban, and related views. Changes save automatically.
          </p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
              <div className="divide-y rounded-md border bg-card">
                {displayMetrics.map((entry) => (
                  <SortableDisplayMetricRow
                    key={sortableIdForDisplayMetric(entry)}
                    entry={entry}
                    trackedMetrics={project.metrics.trackedMetrics}
                    disabled={isPending}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      ) : null}
    </div>
  );
}
