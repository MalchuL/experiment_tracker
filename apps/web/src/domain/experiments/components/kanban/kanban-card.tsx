"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Experiment } from "@/domain/experiments/types";

interface KanbanCardProps {
  experiment: Experiment;
  onClick: () => void;
}

export function KanbanCard({ experiment, onClick }: KanbanCardProps) {
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

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        className="hover-elevate active-elevate-2 cursor-pointer"
        onClick={onClick}
        data-testid={`kanban-card-${experiment.id}`}
      >
        <CardContent className="p-3">
          <div className="flex items-start gap-2">
            <div
              className="w-2 h-full rounded-full mt-1 flex-shrink-0"
              style={{ backgroundColor: experiment.color }}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{experiment.name}</p>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                {experiment.id.slice(0, 8)}
              </p>
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

