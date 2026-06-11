"use client";

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
import { GripVertical } from "lucide-react";

type MetricsOrderListProps = {
  metricNames: string[];
  onReorder: (names: string[]) => void;
  disabled?: boolean;
};

function SortableMetricRow({ name, disabled }: { name: string; disabled: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: name,
    disabled,
  });

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
      data-testid={`metrics-order-row-${name.replace(/[^a-zA-Z0-9-_]/g, "-")}`}
    >
      <button
        type="button"
        className="cursor-grab touch-none rounded-md p-1 text-muted-foreground hover:bg-muted active:cursor-grabbing disabled:pointer-events-none disabled:opacity-40"
        {...attributes}
        {...listeners}
        disabled={disabled}
        aria-label={`Reorder ${name}`}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <span className="min-w-0 flex-1 truncate font-medium" title={name}>
        {name}
      </span>
    </div>
  );
}

export function MetricsOrderList({ metricNames, onReorder, disabled = false }: MetricsOrderListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = metricNames.indexOf(String(active.id));
    const newIndex = metricNames.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    onReorder(arrayMove(metricNames, oldIndex, newIndex));
  };

  if (metricNames.length === 0) return null;

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={metricNames} strategy={verticalListSortingStrategy}>
        <div className="divide-y rounded-md border bg-card">
          {metricNames.map((name) => (
            <SortableMetricRow key={name} name={name} disabled={disabled} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
