"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, arrayMove, horizontalListSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useExperiments } from "@/domain/experiments/hooks";
import type { Experiment } from "@/domain/experiments/types";
import { HparamsCompareTab } from "../hparams/components";
import { FilesCompareTab } from "../snapshots/components";
import { ExperimentNameTooltip } from "./experiment-name-tooltip";

interface CompareShellProps {
  projectId: string;
}

export function CompareShell({ projectId }: CompareShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pendingExperimentId, setPendingExperimentId] = useState<string>("");
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );
  const { experiments, isLoading } = useExperiments(projectId, {
    includeFeatures: false,
  });

  const urlSelectedIds = useMemo(() => {
    const params = searchParams.getAll("exp");
    return Array.from(new Set(params.filter(Boolean)));
  }, [searchParams]);
  const [selectedIds, setSelectedIds] = useState<string[]>(urlSelectedIds);
  const pendingUrlOrderRef = useRef<string | null>(null);

  useEffect(() => {
    const urlOrder = urlSelectedIds.join(",");
    if (pendingUrlOrderRef.current === urlOrder) {
      pendingUrlOrderRef.current = null;
      return;
    }
    if (pendingUrlOrderRef.current !== null) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setSelectedIds(urlSelectedIds);
    });
    return () => {
      cancelled = true;
    };
  }, [urlSelectedIds]);

  const experimentsById = useMemo(() => {
    return new Map(experiments.map((experiment) => [experiment.id, experiment]));
  }, [experiments]);

  const selectedExperiments = selectedIds.map((id) => {
    return experimentsById.get(id) ?? fallbackExperiment(projectId, id);
  });
  const availableExperiments = experiments.filter(
    (experiment) => !selectedIds.includes(experiment.id)
  );

  const replaceSelectedIds = (ids: string[]) => {
    setSelectedIds(ids);
    pendingUrlOrderRef.current = ids.join(",");
    const params = new URLSearchParams(searchParams.toString());
    params.delete("exp");
    ids.forEach((id) => params.append("exp", id));
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const oldIndex = selectedIds.indexOf(String(active.id));
    const newIndex = selectedIds.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    replaceSelectedIds(arrayMove(selectedIds, oldIndex, newIndex));
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b bg-background px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-lg font-semibold">Compare</div>
          <div className="flex min-w-72 items-center gap-2">
            <Select
              value={pendingExperimentId}
              onValueChange={(experimentId) => {
                replaceSelectedIds([...selectedIds, experimentId]);
                setPendingExperimentId("");
              }}
            >
              <SelectTrigger className="w-72">
                <SelectValue placeholder={isLoading ? "Loading experiments..." : "Add experiment"} />
              </SelectTrigger>
              <SelectContent>
                {availableExperiments.map((experiment) => (
                  <SelectItem key={experiment.id} value={experiment.id}>
                    <ExperimentNameWithColor experiment={experiment} />
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={selectedIds} strategy={horizontalListSortingStrategy}>
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                {selectedExperiments.map((experiment) => (
                  <SelectedExperimentChip
                    key={experiment.id}
                    experiment={experiment}
                    isBaseline={experiment.id === selectedIds[0]}
                    onRemove={() =>
                      replaceSelectedIds(selectedIds.filter((id) => id !== experiment.id))
                    }
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      </div>

      <Tabs defaultValue="files" className="flex min-h-0 flex-1 flex-col">
        <div className="border-b px-5 py-2">
          <TabsList>
            <TabsTrigger value="files">Files</TabsTrigger>
            <TabsTrigger value="hparams">HParams</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="files" className="m-0 flex min-h-0 flex-1">
          <FilesCompareTab
            projectId={projectId}
            allExperiments={experiments}
            selectedExperiments={selectedExperiments}
            onEnsureExperimentSelected={(experimentId) => {
              if (!selectedIds.includes(experimentId)) {
                replaceSelectedIds([...selectedIds, experimentId]);
              }
            }}
          />
        </TabsContent>
        <TabsContent value="hparams" className="m-0 flex min-h-0 flex-1">
          <HparamsCompareTab
            projectId={projectId}
            allExperiments={experiments}
            selectedExperiments={selectedExperiments}
            onEnsureExperimentSelected={(experimentId) => {
              if (!selectedIds.includes(experimentId)) {
                replaceSelectedIds([...selectedIds, experimentId]);
              }
            }}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ExperimentNameWithColor({
  experiment,
}: {
  experiment: Pick<Experiment, "name" | "color">;
}) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: experiment.color || "#3b82f6" }}
      />
      <span className="min-w-0 truncate">{experiment.name}</span>
    </span>
  );
}

function SelectedExperimentChip({
  experiment,
  isBaseline,
  onRemove,
}: {
  experiment: Pick<Experiment, "id" | "name" | "color">;
  isBaseline: boolean;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: experiment.id,
  });
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
      className="flex h-9 max-w-72 items-center gap-1 rounded-md border bg-muted/40 pl-1 pr-1 text-sm"
    >
      <button
        type="button"
        className="cursor-grab touch-none rounded p-1 text-muted-foreground hover:bg-muted active:cursor-grabbing"
        aria-label={`Reorder ${experiment.name}`}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-3.5 w-3.5" />
      </button>
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: experiment.color || "#3b82f6" }}
      />
      <ExperimentNameTooltip name={experiment.name}>
        <span className="min-w-0 truncate" tabIndex={0}>{experiment.name}</span>
      </ExperimentNameTooltip>
      {isBaseline ? <span className="text-[10px] text-muted-foreground">baseline</span> : null}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 shrink-0"
        onClick={onRemove}
        aria-label={`Remove ${experiment.name}`}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}

function fallbackExperiment(projectId: string, id: string): Experiment {
  return {
    id,
    projectId,
    name: id,
    description: "",
    status: "planned",
    parentExperimentId: null,
    rootExperimentId: null,
    progress: 0,
    color: "#3b82f6",
    order: 0,
    tags: [],
    createdAt: "",
    startedAt: null,
    completedAt: null,
  };
}
