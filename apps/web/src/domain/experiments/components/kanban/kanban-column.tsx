"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { KanbanColumn } from "@/domain/experiments/types";
import { Experiment } from "@/domain/experiments/types";
import { KanbanCard } from "./kanban-card";

interface KanbanColumnProps {
  column: KanbanColumn;
  experiments: Experiment[];
  onExperimentClick: (experimentId: string) => void;
}

export function KanbanColumnComponent({
  column,
  experiments,
  onExperimentClick,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  const Icon = column.icon;

  return (
    <Card
      className="flex flex-col h-[calc(100vh-16rem)]"
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
      <CardContent className="flex-1 p-2 overflow-hidden">
        <ScrollArea className="h-full">
          <div
            ref={setNodeRef}
            className={`space-y-2 pr-2 min-h-[100px] ${
              isOver ? "bg-accent/30 rounded-md" : ""
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
                  className="text-center py-8 text-sm text-muted-foreground border-2 border-dashed rounded-md"
                  data-testid={`kanban-drop-${column.id}`}
                >
                  Drop here
                </div>
              ) : (
                experiments.map((experiment) => (
                  <KanbanCard
                    key={experiment.id}
                    experiment={experiment}
                    onClick={() => onExperimentClick(experiment.id)}
                  />
                ))
              )}
            </SortableContext>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

