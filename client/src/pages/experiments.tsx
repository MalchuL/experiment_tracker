import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { ExperimentSidebar } from "@/components/experiment-sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useExperimentStore } from "@/stores/experiment-store";
import { Plus, FlaskConical, MoreVertical, GitBranch, Calendar, TrendingUp, TrendingDown } from "lucide-react";
import type { Experiment, InsertExperiment, Project } from "@shared/schema";
import { insertExperimentSchema, EXPERIMENT_COLORS } from "@shared/schema";
import { format } from "date-fns";
import { z } from "zod";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
});

type FormData = z.infer<typeof formSchema>;

export default function Experiments() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();
  const {
    selectedExperimentId,
    selectedProjectId,
    setSelectedExperimentId,
    setSelectedProjectId,
  } = useExperimentStore();

  const { data: experiments, isLoading } = useQuery<Experiment[]>({
    queryKey: selectedProjectId
      ? ["/api/projects", selectedProjectId, "experiments"]
      : ["/api/experiments"],
  });

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const { data: aggregatedMetrics } = useQuery<Record<string, Record<string, number | null>>>({
    queryKey: ["/api/projects", selectedProjectId, "metrics"],
    enabled: !!selectedProjectId,
  });

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      projectId: selectedProjectId || "",
      name: "",
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
        queryKey: ["/api/projects", selectedProjectId, "experiments"],
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
        description: "Failed to create experiment. Please try again.",
        variant: "destructive",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      return apiRequest("DELETE", `/api/experiments/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      queryClient.invalidateQueries({ queryKey: ["/api/projects"] });
      queryClient.invalidateQueries({
        queryKey: ["/api/projects", selectedProjectId, "experiments"],
      });
      toast({
        title: "Experiment deleted",
        description: "The experiment has been deleted.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to delete experiment.",
        variant: "destructive",
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
      features,
      parentExperimentId: data.parentExperimentId || null,
    });
  };

  const formProjectId = form.watch("projectId");
  const projectExperiments = useMemo(() => {
    if (!experiments) return [];
    return experiments.filter((e) => e.projectId === formProjectId);
  }, [experiments, formProjectId]);

  const formatMetricValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "NaN";
    return value.toFixed(4);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Experiments" description="Manage your research experiments" />
        <ListSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description="Track and manage your ML/DS experiments"
        actions={
          <div className="flex items-center gap-2">
            <Select
              value={selectedProjectId || "all"}
              onValueChange={(v) => setSelectedProjectId(v === "all" ? null : v)}
            >
              <SelectTrigger className="w-48" data-testid="select-project-filter">
                <SelectValue placeholder="All Projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="button-create-experiment">
                  <Plus className="w-4 h-4 mr-2" />
                  New Experiment
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Experiment</DialogTitle>
                  <DialogDescription>
                    Create a new experiment to track your research run.
                  </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                      control={form.control}
                      name="projectId"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Project</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger data-testid="select-project">
                                <SelectValue placeholder="Select a project" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {projects?.map((project) => (
                                <SelectItem key={project.id} value={project.id}>
                                  {project.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="e.g., exp_001_lr_sweep"
                              data-testid="input-experiment-name"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Status</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                              <FormControl>
                                <SelectTrigger data-testid="select-status">
                                  <SelectValue placeholder="Select status" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                <SelectItem value="planned">Planned</SelectItem>
                                <SelectItem value="running">Running</SelectItem>
                                <SelectItem value="complete">Complete</SelectItem>
                                <SelectItem value="failed">Failed</SelectItem>
                              </SelectContent>
                            </Select>
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
                            <div className="flex gap-1 flex-wrap">
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
                    </div>
                    <FormField
                      control={form.control}
                      name="parentExperimentId"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Parent Experiment (Optional)</FormLabel>
                          <Select
                            onValueChange={(value) =>
                              field.onChange(value === "none" ? null : value)
                            }
                            value={field.value || "none"}
                          >
                            <FormControl>
                              <SelectTrigger data-testid="select-parent">
                                <SelectValue placeholder="Select parent experiment" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="none">No parent (root experiment)</SelectItem>
                              {projectExperiments.map((exp) => (
                                <SelectItem key={exp.id} value={exp.id}>
                                  {exp.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
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
                        {createMutation.isPending ? "Creating..." : "Create Experiment"}
                      </Button>
                    </div>
                  </form>
                </Form>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      {!experiments || experiments.length === 0 ? (
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
          <Table>
            <TableHeader>
              <TableRow>
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
                <TableHead className="w-[100px]">Created</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {experiments.map((experiment) => {
                const expMetrics = aggregatedMetrics?.[experiment.id];
                const parentExp = experiments.find(
                  (e) => e.id === experiment.parentExperimentId
                );

                return (
                  <TableRow
                    key={experiment.id}
                    className="cursor-pointer hover-elevate"
                    onClick={() => setSelectedExperimentId(experiment.id)}
                    data-testid={`row-experiment-${experiment.id}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: experiment.color }}
                        />
                        <div className="min-w-0">
                          <p className="font-medium truncate">{experiment.name}</p>
                          <p className="text-xs text-muted-foreground font-mono">
                            {experiment.id.slice(0, 8)}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={experiment.status} size="sm" />
                        {experiment.status === "running" && (
                          <span className="text-xs text-muted-foreground">
                            {experiment.progress}%
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {parentExp ? (
                        <Badge variant="outline" className="text-xs">
                          <GitBranch className="w-3 h-3 mr-1" />
                          {parentExp.name.slice(0, 15)}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">root</span>
                      )}
                    </TableCell>
                    {selectedProject?.metrics.map((metric) => (
                      <TableCell
                        key={metric.name}
                        className="text-right font-mono text-sm"
                      >
                        <span
                          className={
                            expMetrics?.[metric.name] === null ||
                            expMetrics?.[metric.name] === undefined
                              ? "text-muted-foreground"
                              : ""
                          }
                        >
                          {formatMetricValue(expMetrics?.[metric.name])}
                        </span>
                      </TableCell>
                    ))}
                    <TableCell className="text-muted-foreground text-xs">
                      {format(new Date(experiment.createdAt), "MMM d")}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          asChild
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteMutation.mutate(experiment.id);
                            }}
                            data-testid={`button-delete-experiment-${experiment.id}`}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
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
