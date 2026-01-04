"use client";

import { useState, useMemo } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from "@dnd-kit/core";
import { Experiment, ExperimentStatusType, KANBAN_COLUMNS } from "@/domain/experiments/types";
import { KanbanColumnComponent } from "./kanban-column";
import { KanbanCardOverlay } from "./kanban-card-overlay";

interface KanbanBoardProps {
  experiments: Experiment[];
  onExperimentClick: (experimentId: string) => void;
  onStatusUpdate: (experimentId: string, status: ExperimentStatusType) => void;
}

export function KanbanBoard({
  experiments,
  onExperimentClick,
  onStatusUpdate,
}: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const getExperimentsByStatus = (status: string) => {
    return experiments.filter((e) => e.status === status);
  };

  const activeExperiment = useMemo(() => {
    if (!activeId) return null;
    return experiments.find((e) => e.id === activeId) || null;
  }, [activeId, experiments]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const experimentId = active.id as string;
    const overId = over.id as string;

    let targetColumnId: string | null = null;

    // Check if dropped on a column
    if (KANBAN_COLUMNS.some((col) => col.id === overId)) {
      targetColumnId = overId;
    } else {
      // Check if dropped on another experiment
      const targetExperiment = experiments.find((e) => e.id === overId);
      if (targetExperiment) {
        targetColumnId = targetExperiment.status;
      }
    }

    if (targetColumnId) {
      const experiment = experiments.find((e) => e.id === experimentId);
      if (experiment && experiment.status !== targetColumnId) {
        const newStatus = targetColumnId as ExperimentStatusType;
        onStatusUpdate(experimentId, newStatus);
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 flex-1">
        {KANBAN_COLUMNS.map((column) => {
          const columnExperiments = getExperimentsByStatus(column.id);

          return (
            <KanbanColumnComponent
              key={column.id}
              column={column}
              experiments={columnExperiments}
              onExperimentClick={onExperimentClick}
            />
          );
        })}
      </div>
      <DragOverlay>
        {activeExperiment && (
          <KanbanCardOverlay experiment={activeExperiment} />
        )}
      </DragOverlay>
    </DndContext>
  );
}

