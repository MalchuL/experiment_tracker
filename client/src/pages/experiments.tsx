import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
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
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { ExperimentSidebar } from "@/components/experiment-sidebar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useExperimentStore } from "@/stores/experiment-store";
import { useProjectId } from "@/hooks/use-project-id";
import { Plus, FlaskConical, GripVertical, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import type { Experiment, InsertExperiment, Project } from "@shared/schema";
import { insertExperimentSchema, EXPERIMENT_COLORS } from "@shared/schema";
import { format } from "date-fns";
import { z } from "zod";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const formSchema = insertExperimentSchema.extend({
  featuresJson: z.string().optional(),
  color: z.string().optional(),
  description: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface SortableRowProps {
  experiment: Experiment;
  onClick: () => void;
  projectMetrics?: Project["metrics"];
  expMetrics?: Record<string, number | null>;
  parentName?: string;
}

function SortableRow({ experiment, onClick, projectMetrics, expMetrics, parentName }: SortableRowProps) {
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

  const formatMetricValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "NaN";
    return value.toFixed(4);
  };

  return (
    <TableRow
      ref={setNodeRef}
      style={style}
      className="cursor-pointer hover-elevate"
      onClick={onClick}
      data-testid={`row-experiment-${experiment.id}`}
    >
      <TableCell>
        <div
          className="cursor-grab active:cursor-grabbing p-1"
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: experiment.color }}
          />
          <div>
            <p className="font-medium truncate">{experiment.name}</p>
            {experiment.description && (
              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                {experiment.description}
              </p>
            )}
          </div>
        </div>
      </TableCell>
      <TableCell>
        <StatusBadge status={experiment.status} />
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {parentName || "-"}
      </TableCell>
      {projectMetrics?.map((metric) => (
        <TableCell key={metric.name} className="text-right font-mono text-sm">
          {formatMetricValue(expMetrics?.[metric.name])}
        </TableCell>
      ))}
      <TableCell className="text-muted-foreground text-sm">
        {format(new Date(experiment.createdAt), "MMM d")}
      </TableCell>
    </TableRow>
  );
}

export default function Experiments() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();
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

  const { data: experiments = [], isLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/projects", projectId, "experiments"],
    enabled: !!projectId,
    staleTime: 0,
  });

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const { data: aggregatedMetrics } = useQuery<Record<string, Record<string, number | null>>>({
    queryKey: ["/api/projects", projectId, "metrics"],
    enabled: !!projectId,
  });

  const selectedProject = projects?.find((p) => p.id === projectId);

  const sortedExperiments = useMemo(() => {
    if (!experiments) return [];
    return [...experiments].sort((a, b) => a.order - b.order);
  }, [experiments]);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      projectId: projectId || "",
      name: "",
      description: "",
      status: "planned",
      parentExperimentId: null,
      features: {},
      featuresJson: "",
      color: EXPERIMENT_COLORS[0],
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: InsertExperiment) => {
      return apiRequest("POST", "/api/experiments", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      queryClient.invalidateQueries({ queryKey: ["/api/projects"] });
      queryClient.invalidateQueries({
        queryKey: ["/api/projects", projectId, "experiments"],
      });
      setIsDialogOpen(false);
      form.reset();
      toast({
        title: "Experiment created",
        description: "Your new experiment has been created successfully.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to create experiment.",
        variant: "destructive",
      });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: async (experimentIds: string[]) => {
      return apiRequest("PATCH", `/api/projects/${projectId}/experiments/reorder`, {
        experimentIds,
      });
    },
    onMutate: async (experimentIds: string[]) => {
      await queryClient.cancelQueries({
        queryKey: ["/api/projects", projectId, "experiments"],
      });

      const previousExperiments = queryClient.getQueryData<Experiment[]>([
        "/api/projects",
        projectId,
        "experiments",
      ]);

      queryClient.setQueryData<Experiment[]>(
        ["/api/projects", projectId, "experiments"],
        (old) => {
          if (!old) return old;
          return experimentIds.map((id, index) => {
            const exp = old.find((e) => e.id === id);
            return exp ? { ...exp, order: index } : null;
          }).filter(Boolean) as Experiment[];
        }
      );

      return { previousExperiments };
    },
    onError: (_err, _experimentIds, context) => {
      if (context?.previousExperiments) {
        queryClient.setQueryData(
          ["/api/projects", projectId, "experiments"],
          context.previousExperiments
        );
      }
      toast({
        title: "Error",
        description: "Failed to reorder experiments.",
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["/api/projects", projectId, "experiments"],
      });
    },
  });

  const onSubmit = (data: FormData) => {
    let features = {};
    if (data.featuresJson) {
      try {
        features = JSON.parse(data.featuresJson);
      } catch {
        toast({
          title: "Invalid JSON",
          description: "Features must be valid JSON.",
          variant: "destructive",
        });
        return;
      }
    }

    createMutation.mutate({
      ...data,
      projectId: projectId || data.projectId,
      features,
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = sortedExperiments.findIndex((e) => e.id === active.id);
    const newIndex = sortedExperiments.findIndex((e) => e.id === over.id);

    const newOrder = arrayMove(sortedExperiments, oldIndex, newIndex);
    reorderMutation.mutate(newOrder.map((e) => e.id));
  };

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its experiments.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Experiments" description="Loading..." />
        <ListSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description={`Experiments for "${selectedProject?.name}". Drag to reorder.`}
        actions={
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="button-create-experiment">
                <Plus className="w-4 h-4 mr-2" />
                New Experiment
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Create Experiment</DialogTitle>
                <DialogDescription>
                  Add a new experiment to "{selectedProject?.name}".
                </DialogDescription>
              </DialogHeader>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="exp_001_lr_sweep"
                            data-testid="input-experiment-name"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Experiment description..."
                            className="resize-none"
                            data-testid="input-experiment-description"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="color"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Color</FormLabel>
                        <div className="flex gap-2 flex-wrap">
                          {EXPERIMENT_COLORS.map((color) => (
                            <button
                              key={color}
                              type="button"
                              className={`w-6 h-6 rounded-full border-2 ${
                                field.value === color
                                  ? "border-foreground"
                                  : "border-transparent"
                              }`}
                              style={{ backgroundColor: color }}
                              onClick={() => field.onChange(color)}
                              data-testid={`color-${color}`}
                            />
                          ))}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="featuresJson"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Features (JSON)</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder='{"optimizer": "AdamW", "lr": 0.0001}'
                            className="resize-none font-mono text-sm"
                            data-testid="input-features"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={createMutation.isPending}
                      data-testid="button-submit-experiment"
                    >
                      {createMutation.isPending ? "Creating..." : "Create"}
                    </Button>
                  </div>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        }
      />

      {!sortedExperiments.length ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description="Create your first experiment to start tracking your research runs."
          action={
            <Button
              onClick={() => setIsDialogOpen(true)}
              data-testid="button-empty-create-experiment"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Experiment
            </Button>
          }
        />
      ) : (
        <Card>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]"></TableHead>
                  <TableHead className="w-[200px]">Experiment</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Parent</TableHead>
                  {selectedProject?.metrics.map((metric) => (
                    <TableHead key={metric.name} className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {metric.name}
                        {metric.direction === "minimize" ? (
                          <TrendingDown className="w-3 h-3" />
                        ) : (
                          <TrendingUp className="w-3 h-3" />
                        )}
                      </div>
                    </TableHead>
                  ))}
                  <TableHead className="w-[80px]">Created</TableHead>
                </TableRow>
              </TableHeader>
              <SortableContext
                items={sortedExperiments.map((e) => e.id)}
                strategy={verticalListSortingStrategy}
              >
                <TableBody>
                  {sortedExperiments.map((experiment) => {
                    const parent = sortedExperiments.find(
                      (e) => e.id === experiment.parentExperimentId
                    );
                    return (
                      <SortableRow
                        key={experiment.id}
                        experiment={experiment}
                        onClick={() => setSelectedExperimentId(experiment.id)}
                        projectMetrics={selectedProject?.metrics}
                        expMetrics={aggregatedMetrics?.[experiment.id]}
                        parentName={parent?.name}
                      />
                    );
                  })}
                </TableBody>
              </SortableContext>
            </Table>
          </DndContext>
        </Card>
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={selectedProject?.metrics}
          aggregatedMetrics={aggregatedMetrics?.[selectedExperimentId] || undefined}
        />
      )}
    </div>
  );
}
