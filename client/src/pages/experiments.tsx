import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useSearch } from "wouter";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
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
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Plus, FlaskConical, MoreVertical, GitBranch, Calendar } from "lucide-react";
import type { Experiment, InsertExperiment, Project } from "@shared/schema";
import { insertExperimentSchema } from "@shared/schema";
import { format } from "date-fns";
import { z } from "zod";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const formSchema = insertExperimentSchema.extend({
  featuresJson: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

export default function Experiments() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();
  const searchString = useSearch();
  const params = new URLSearchParams(searchString);
  const preselectedProjectId = params.get("projectId");

  const { data: experiments, isLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/experiments"],
  });

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["/api/projects"],
  });

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      projectId: preselectedProjectId || "",
      name: "",
      status: "planned",
      parentExperimentId: null,
      features: {},
      featuresJson: "",
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

  const selectedProjectId = form.watch("projectId");
  const projectExperiments = experiments?.filter(e => e.projectId === selectedProjectId) || [];

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
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                    name="parentExperimentId"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Parent Experiment (Optional)</FormLabel>
                        <Select 
                          onValueChange={(value) => field.onChange(value === "none" ? null : value)} 
                          defaultValue={field.value || "none"}
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
        }
      />

      {!experiments || experiments.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description="Create your first experiment to start tracking your research runs."
          action={
            <Button onClick={() => setIsDialogOpen(true)} data-testid="button-empty-create-experiment">
              <Plus className="w-4 h-4 mr-2" />
              Create Experiment
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {experiments.map((experiment) => {
            const project = projects?.find(p => p.id === experiment.projectId);
            
            return (
              <Link key={experiment.id} href={`/experiments/${experiment.id}`}>
                <Card 
                  className="hover-elevate active-elevate-2 cursor-pointer"
                  data-testid={`card-experiment-${experiment.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="flex items-center justify-center w-10 h-10 rounded-md bg-accent flex-shrink-0">
                          <FlaskConical className="w-5 h-5 text-accent-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium truncate">{experiment.name}</p>
                            <span className="text-xs text-muted-foreground font-mono">
                              {experiment.id.slice(0, 8)}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 flex-wrap">
                            {project && <span>{project.name}</span>}
                            {experiment.parentExperimentId && (
                              <span className="flex items-center gap-1">
                                <GitBranch className="w-3 h-3" />
                                from {experiment.parentExperimentId.slice(0, 8)}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {format(new Date(experiment.createdAt), "MMM d")}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        {experiment.status === "running" && (
                          <div className="w-24">
                            <Progress value={experiment.progress} className="h-2" />
                          </div>
                        )}
                        <StatusBadge status={experiment.status} />
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={(e) => {
                                e.preventDefault();
                                deleteMutation.mutate(experiment.id);
                              }}
                              data-testid={`button-delete-experiment-${experiment.id}`}
                            >
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
