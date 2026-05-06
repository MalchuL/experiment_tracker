"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Experiment } from "@/domain/experiments/types";
import { getExperimentSelectionSurfaceStyle } from "@/domain/experiments/experiment-selection-style";
import { cn } from "@/lib/utils";
import { ExperimentTruncatedText } from "@/domain/experiments/components/experiment-truncated-text";

interface KanbanCardProps {
  experiment: Experiment;
  isSelected?: boolean;
  onClick: () => void;
}

export function KanbanCard({ experiment, isSelected, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: experiment.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const selectionStyle = isSelected
    ? getExperimentSelectionSurfaceStyle(experiment.color)
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="min-w-0 w-full max-w-full"
      {...attributes}
      {...listeners}
    >
      <Card
        data-state={isSelected ? "selected" : undefined}
        className={cn(
          "min-w-0 w-full max-w-full overflow-hidden hover-elevate active-elevate-2 cursor-pointer",
          isSelected && "transition-colors"
        )}
        style={selectionStyle}
        onClick={onClick}
        data-testid={`kanban-card-${experiment.id}`}
      >
        <CardContent className="min-w-0 p-3">
          <div className="flex min-w-0 items-center gap-2">
            <div
              className="h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: experiment.color }}
            />
            <div className="min-w-0 w-full flex-1 overflow-hidden">
              <ExperimentTruncatedText
                text={experiment.name}
                className="text-sm font-medium"
                showTooltip="always"
                lineClamp={2}
              />
              {experiment.description ? (
                <ExperimentTruncatedText
                  text={experiment.description}
                  className="mt-0.5 text-xs text-muted-foreground"
                  showTooltip="always"
                  lineClamp={3}
                />
              ) : null}
              <p className="mt-0.5 font-mono text-xs text-muted-foreground">{experiment.id.slice(0, 8)}</p>
            </div>
          </div>
          {experiment.status === "running" && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>Progress</span>
                <span>{experiment.progress}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${experiment.progress}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

