"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KanbanColumn } from "@/domain/experiments/types";
import { Experiment } from "@/domain/experiments/types";
import { KanbanCard } from "./kanban-card";

interface KanbanColumnProps {
  column: KanbanColumn;
  experiments: Experiment[];
  selectedExperimentId?: string | null;
  onExperimentClick: (experimentId: string) => void;
}

export function KanbanColumnComponent({
  column,
  experiments,
  selectedExperimentId,
  onExperimentClick,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  const Icon = column.icon;

  return (
    <Card
      className="flex h-[calc(100vh-16rem)] min-w-0 max-w-full flex-col overflow-hidden"
      data-testid={`kanban-column-${column.id}`}
    >
      <CardHeader className={`rounded-t-md ${column.className}`}>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Icon className="w-4 h-4" />
          {column.title}
          <span className="ml-auto text-xs bg-background/80 px-2 py-0.5 rounded-full">
            {experiments.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 overflow-hidden p-2">
        {/* Native scroll: Radix ScrollArea viewport uses `display:table` on its inner wrapper, which
            lets wide card text expand the column past the grid track. */}
        <div className="h-full min-h-0 min-w-0 max-w-full overflow-y-auto overflow-x-hidden overscroll-y-contain">
          <div
            ref={setNodeRef}
            className={`min-h-[100px] min-w-0 max-w-full space-y-2 pr-1 ${
              isOver ? "rounded-md bg-accent/30" : ""
            }`}
            data-column={column.id}
          >
            <SortableContext
              id={column.id}
              items={experiments.map((e) => e.id)}
              strategy={verticalListSortingStrategy}
            >
              {experiments.length === 0 ? (
                <div
                  className="rounded-md border-2 border-dashed py-8 text-center text-sm text-muted-foreground"
                  data-testid={`kanban-drop-${column.id}`}
                >
                  Drop here
                </div>
              ) : (
                experiments.map((experiment) => (
                  <KanbanCard
                    key={experiment.id}
                    experiment={experiment}
                    isSelected={selectedExperimentId === experiment.id}
                    onClick={() => onExperimentClick(experiment.id)}
                  />
                ))
              )}
            </SortableContext>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

