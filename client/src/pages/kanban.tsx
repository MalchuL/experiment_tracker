import { useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  DragOverEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { ExperimentSidebar } from "@/components/experiment-sidebar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useExperimentStore } from "@/stores/experiment-store";
import { useProjectId } from "@/hooks/use-project-id";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { FlaskConical, Plus, Clock, Play, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { Experiment, Project, ExperimentStatusType } from "@shared/schema";
import { ExperimentStatus } from "@shared/schema";

const columns = [
  { id: ExperimentStatus.PLANNED, title: "Planned", icon: Clock, className: "bg-muted/50" },
  { id: ExperimentStatus.RUNNING, title: "Running", icon: Play, className: "bg-blue-500/10" },
  { id: ExperimentStatus.COMPLETE, title: "Complete", icon: CheckCircle2, className: "bg-green-500/10" },
  { id: ExperimentStatus.FAILED, title: "Failed", icon: XCircle, className: "bg-red-500/10" },
];

interface SortableExperimentCardProps {
  experiment: Experiment;
  onClick: () => void;
}

function SortableExperimentCard({ experiment, onClick }: SortableExperimentCardProps) {
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

function ExperimentCardOverlay({ experiment }: { experiment: Experiment }) {
  return (
    <Card className="shadow-lg rotate-2 w-64">
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
      </CardContent>
    </Card>
  );
}

interface DroppableColumnProps {
  columnId: string;
  children: React.ReactNode;
}

function DroppableColumn({ columnId, children }: DroppableColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: columnId,
  });

  return (
    <div
      ref={setNodeRef}
      className={`space-y-2 pr-2 min-h-[100px] ${isOver ? "bg-accent/30 rounded-md" : ""}`}
      data-column={columnId}
    >
      {children}
    </div>
  );
}

export default function Kanban() {
  const { toast } = useToast();
  const [activeId, setActiveId] = useState<string | null>(null);
  const projectId = useProjectId();
  const {
    selectedExperimentId,
    setSelectedExperimentId,
  } = useExperimentStore();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const { data: experiments = [], isLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/projects", projectId, "experiments"],
    enabled: !!projectId,
  });

  const { data: aggregatedMetrics } = useQuery<Record<string, Record<string, number | null>>>({
    queryKey: ["/api/projects", projectId, "metrics"],
    enabled: !!projectId,
  });

  const selectedProject = projects?.find((p) => p.id === projectId);

  const updateStatusMutation = useMutation({
    mutationFn: async ({
      experimentId,
      status,
    }: {
      experimentId: string;
      status: ExperimentStatusType;
    }) => {
      return apiRequest("PATCH", `/api/experiments/${experimentId}`, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({
        queryKey: ["/api/projects", projectId, "experiments"],
      });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      toast({
        title: "Status updated",
        description: "Experiment moved to new column.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to update experiment status.",
        variant: "destructive",
      });
    },
  });

  const filteredExperiments = useMemo(() => {
    if (!experiments || !projectId) return [];
    return experiments;
  }, [experiments, projectId]);

  const getExperimentsByStatus = (status: string) => {
    return filteredExperiments.filter((e) => e.status === status);
  };

  const activeExperiment = useMemo(() => {
    if (!activeId) return null;
    return filteredExperiments.find((e) => e.id === activeId) || null;
  }, [activeId, filteredExperiments]);

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

    if (columns.some((col) => col.id === overId)) {
      targetColumnId = overId;
    } else {
      const targetExperiment = filteredExperiments.find((e) => e.id === overId);
      if (targetExperiment) {
        targetColumnId = targetExperiment.status;
      }
    }

    if (targetColumnId) {
      const experiment = filteredExperiments.find((e) => e.id === experimentId);
      if (experiment && experiment.status !== targetColumnId) {
        updateStatusMutation.mutate({
          experimentId,
          status: targetColumnId as ExperimentStatusType,
        });
      }
    }
  };

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its Kanban board.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Kanban View"
          description="Drag experiments between columns to update status"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      <PageHeader
        title="Kanban View"
        description={`Kanban board for "${selectedProject?.name}"`}
      />

      {filteredExperiments.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description={
            projectId
              ? "No experiments in this project."
              : "Create experiments to organize them by status."
          }
        />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 flex-1">
            {columns.map((column) => {
              const columnExperiments = getExperimentsByStatus(column.id);
              const Icon = column.icon;

              return (
                <Card
                  key={column.id}
                  className="flex flex-col h-[calc(100vh-16rem)]"
                  data-testid={`kanban-column-${column.id}`}
                >
                  <CardHeader className={`rounded-t-md ${column.className}`}>
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Icon className="w-4 h-4" />
                      {column.title}
                      <span className="ml-auto text-xs bg-background/80 px-2 py-0.5 rounded-full">
                        {columnExperiments.length}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 p-2 overflow-hidden">
                    <ScrollArea className="h-full">
                      <DroppableColumn columnId={column.id}>
                        <SortableContext
                          id={column.id}
                          items={columnExperiments.map((e) => e.id)}
                          strategy={verticalListSortingStrategy}
                        >
                          {columnExperiments.length === 0 ? (
                            <div
                              className="text-center py-8 text-sm text-muted-foreground border-2 border-dashed rounded-md"
                              data-testid={`kanban-drop-${column.id}`}
                            >
                              Drop here
                            </div>
                          ) : (
                            columnExperiments.map((experiment) => (
                              <SortableExperimentCard
                                key={experiment.id}
                                experiment={experiment}
                                onClick={() => setSelectedExperimentId(experiment.id)}
                              />
                            ))
                          )}
                        </SortableContext>
                      </DroppableColumn>
                    </ScrollArea>
                  </CardContent>
                </Card>
              );
            })}
          </div>
          <DragOverlay>
            {activeExperiment && (
              <ExperimentCardOverlay experiment={activeExperiment} />
            )}
          </DragOverlay>
        </DndContext>
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={selectedProject?.metrics}
          aggregatedMetrics={
            aggregatedMetrics?.[selectedExperimentId] || undefined
          }
        />
      )}
    </div>
  );
}
