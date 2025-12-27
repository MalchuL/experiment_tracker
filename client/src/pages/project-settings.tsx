import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useProjectId } from "@/hooks/use-project-id";
import { Settings, Plus, Trash2, TrendingUp, TrendingDown, AlertCircle, Eye, ChevronDown, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Project, ProjectMetric } from "@shared/schema";
import { z } from "zod";

const settingsSchema = z.object({
  namingPattern: z.string(),
  displayMetrics: z.array(z.string()),
});

type SettingsFormData = z.infer<typeof settingsSchema>;

const basicInfoSchema = z.object({
  name: z.string().min(1, "Project name is required"),
  description: z.string().optional(),
  owner: z.string().optional(),
});

type BasicInfoFormData = z.infer<typeof basicInfoSchema>;

const COMMON_METRICS = [
  "accuracy",
  "loss",
  "val_accuracy",
  "val_loss",
  "train_loss",
  "train_accuracy",
  "precision",
  "recall",
  "f1_score",
  "auc",
  "mse",
  "mae",
  "rmse",
  "r2",
  "perplexity",
  "bleu",
  "rouge",
  "learning_rate",
  "epoch",
  "step",
];

export default function ProjectSettings() {
  const projectId = useProjectId();
  const { toast } = useToast();
  const [newMetricName, setNewMetricName] = useState("");
  const [newMetricDirection, setNewMetricDirection] = useState<"maximize" | "minimize">("maximize");
  const [metricPopoverOpen, setMetricPopoverOpen] = useState(false);

  const { data: project, isLoading } = useQuery<Project>({
    queryKey: ["/api/projects", projectId],
    enabled: !!projectId,
  });

  const form = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      namingPattern: project?.settings?.namingPattern || "{num}_from_{parent}_{change}",
      displayMetrics: project?.settings?.displayMetrics || [],
    },
    values: {
      namingPattern: project?.settings?.namingPattern || "{num}_from_{parent}_{change}",
      displayMetrics: project?.settings?.displayMetrics || [],
    },
  });

  const basicInfoForm = useForm<BasicInfoFormData>({
    resolver: zodResolver(basicInfoSchema),
    defaultValues: {
      name: project?.name || "",
      description: project?.description || "",
      owner: project?.owner || "",
    },
    values: {
      name: project?.name || "",
      description: project?.description || "",
      owner: project?.owner || "",
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: Partial<Project>) => {
      return apiRequest("PATCH", `/api/projects/${projectId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/projects"] });
      queryClient.invalidateQueries({ queryKey: ["/api/projects", projectId] });
      toast({
        title: "Settings saved",
        description: "Project settings have been updated successfully.",
      });
    },
  });

  const onSubmit = (data: SettingsFormData) => {
    updateMutation.mutate({
      settings: data,
    });
  };

  const onSubmitBasicInfo = (data: BasicInfoFormData) => {
    updateMutation.mutate(data);
  };

  const addMetric = () => {
    if (!newMetricName.trim() || !project) return;
    const existingMetric = project.metrics.find(m => m.name === newMetricName.trim());
    if (existingMetric) {
      toast({
        title: "Metric already exists",
        description: `A metric named "${newMetricName}" already exists.`,
        variant: "destructive",
      });
      return;
    }

    const newMetric: ProjectMetric = {
      name: newMetricName.trim(),
      direction: newMetricDirection,
      aggregation: "best",
    };

    updateMutation.mutate({
      metrics: [...project.metrics, newMetric],
    });
    setNewMetricName("");
  };

  const removeMetric = (metricName: string) => {
    if (!project) return;
    updateMutation.mutate({
      metrics: project.metrics.filter(m => m.name !== metricName),
      settings: {
        ...project.settings,
        displayMetrics: project.settings.displayMetrics.filter(m => m !== metricName),
      },
    });
  };

  const updateMetricDirection = (metricName: string, direction: "maximize" | "minimize") => {
    if (!project) return;
    updateMutation.mutate({
      metrics: project.metrics.map(m =>
        m.name === metricName ? { ...m, direction } : m
      ),
    });
  };

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and access its settings.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-6">Loading...</div>;
  }

  if (!project) {
    return <div className="p-6">Project not found</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Project Settings"
        description={`Configure settings for "${project.name}"`}
      />

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Project Information</CardTitle>
            <CardDescription>
              Update your project's basic details.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...basicInfoForm}>
              <form onSubmit={basicInfoForm.handleSubmit(onSubmitBasicInfo)} className="space-y-4">
                <FormField
                  control={basicInfoForm.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Project Name</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="My ML Project"
                          data-testid="input-project-name"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={basicInfoForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Describe your project..."
                          className="resize-none"
                          data-testid="input-project-description"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={basicInfoForm.control}
                  name="owner"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Owner</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Team or individual"
                          data-testid="input-project-owner"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  disabled={updateMutation.isPending}
                  data-testid="button-save-basic-info"
                >
                  Save Project Info
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Naming Pattern
            </CardTitle>
            <CardDescription>
              Configure how new experiments are named when derived from a parent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="namingPattern"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Pattern Template</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="{num}_from_{parent}_{change}"
                          data-testid="input-naming-pattern"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Available variables: {"{num}"} (experiment number), {"{parent}"} (parent name), {"{change}"} (what changed)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  disabled={updateMutation.isPending}
                  data-testid="button-save-settings"
                >
                  Save Settings
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              Display Metrics
            </CardTitle>
            <CardDescription>
              Choose which metrics to show by default on the Scalars page.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {project.metrics.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No metrics configured. Add metrics below first.
              </p>
            ) : (
              <>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="w-full justify-between" data-testid="dropdown-display-metrics">
                      <span className="flex items-center gap-2">
                        <Eye className="w-4 h-4" />
                        {form.watch("displayMetrics").length === 0
                          ? "Select metrics to display..."
                          : form.watch("displayMetrics").length === project.metrics.length
                          ? "All metrics selected"
                          : `${form.watch("displayMetrics").length} of ${project.metrics.length} metrics selected`}
                      </span>
                      <ChevronDown className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-64">
                    <DropdownMenuItem
                      onClick={() => {
                        form.setValue("displayMetrics", project.metrics.map(m => m.name));
                      }}
                      data-testid="menu-select-all-metrics"
                    >
                      <Check className="w-4 h-4 mr-2" />
                      Select All
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => {
                        form.setValue("displayMetrics", []);
                      }}
                      data-testid="menu-clear-all-metrics"
                    >
                      Clear All
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {project.metrics.map((metric) => (
                      <DropdownMenuCheckboxItem
                        key={metric.name}
                        checked={form.watch("displayMetrics").includes(metric.name)}
                        onCheckedChange={(checked) => {
                          const current = form.getValues("displayMetrics");
                          if (checked) {
                            form.setValue("displayMetrics", [...current, metric.name]);
                          } else {
                            form.setValue("displayMetrics", current.filter(m => m !== metric.name));
                          }
                        }}
                        data-testid={`menu-metric-${metric.name}`}
                      >
                        <span className="flex items-center gap-2">
                          {metric.name}
                          {metric.direction === "maximize" ? (
                            <TrendingUp className="w-3 h-3 text-green-500" />
                          ) : (
                            <TrendingDown className="w-3 h-3 text-red-500" />
                          )}
                        </span>
                      </DropdownMenuCheckboxItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                {form.watch("displayMetrics").length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {form.watch("displayMetrics").map((metricName) => (
                      <Badge key={metricName} variant="secondary" className="text-xs">
                        {metricName}
                      </Badge>
                    ))}
                  </div>
                )}

                <Button
                  onClick={form.handleSubmit(onSubmit)}
                  disabled={updateMutation.isPending}
                  className="w-full"
                  data-testid="button-save-display-metrics"
                >
                  Save Display Settings
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tracked Metrics</CardTitle>
            <CardDescription>
              Add or remove metrics and set their optimization direction.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Popover open={metricPopoverOpen} onOpenChange={setMetricPopoverOpen}>
                <PopoverTrigger asChild>
                  <div className="flex-1 relative">
                    <Input
                      placeholder="Type to search metrics (e.g., accuracy)"
                      value={newMetricName}
                      onChange={(e) => {
                        setNewMetricName(e.target.value);
                        if (e.target.value.length > 0) {
                          setMetricPopoverOpen(true);
                        }
                      }}
                      onFocus={() => {
                        if (newMetricName.length > 0 || COMMON_METRICS.length > 0) {
                          setMetricPopoverOpen(true);
                        }
                      }}
                      className="w-full"
                      data-testid="input-new-metric"
                    />
                  </div>
                </PopoverTrigger>
                <PopoverContent className="p-0 w-[300px]" align="start" onOpenAutoFocus={(e) => e.preventDefault()}>
                  <Command>
                    <CommandInput 
                      placeholder="Search metrics..." 
                      value={newMetricName}
                      onValueChange={setNewMetricName}
                    />
                    <CommandList>
                      <CommandEmpty>
                        {newMetricName.trim() ? (
                          <div className="p-2 text-sm">
                            Press Enter or click Add to create "{newMetricName}"
                          </div>
                        ) : (
                          "Type to search or create a metric"
                        )}
                      </CommandEmpty>
                      <CommandGroup heading="Suggestions">
                        {COMMON_METRICS
                          .filter(m => 
                            m.toLowerCase().includes(newMetricName.toLowerCase()) &&
                            !project.metrics.some(pm => pm.name === m)
                          )
                          .slice(0, 8)
                          .map((metricName) => (
                            <CommandItem
                              key={metricName}
                              value={metricName}
                              onSelect={(value) => {
                                setNewMetricName(value);
                                setMetricPopoverOpen(false);
                              }}
                            >
                              {metricName}
                            </CommandItem>
                          ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              <Select
                value={newMetricDirection}
                onValueChange={(v) => setNewMetricDirection(v as "maximize" | "minimize")}
              >
                <SelectTrigger className="w-[140px]" data-testid="select-metric-direction">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="maximize">Maximize</SelectItem>
                  <SelectItem value="minimize">Minimize</SelectItem>
                </SelectContent>
              </Select>
              <Button 
                onClick={() => {
                  addMetric();
                  setMetricPopoverOpen(false);
                }} 
                disabled={!newMetricName.trim()} 
                data-testid="button-add-metric"
              >
                <Plus className="w-4 h-4" />
              </Button>
            </div>

            <div className="space-y-2">
              {project.metrics.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No metrics configured. Add metrics to track experiment performance.
                </p>
              ) : (
                project.metrics.map((metric) => (
                  <div
                    key={metric.name}
                    className="flex items-center justify-between gap-4 p-3 rounded-md border"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{metric.name}</Badge>
                      {metric.direction === "maximize" ? (
                        <TrendingUp className="w-4 h-4 text-green-500" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Select
                        value={metric.direction}
                        onValueChange={(v) =>
                          updateMetricDirection(metric.name, v as "maximize" | "minimize")
                        }
                      >
                        <SelectTrigger className="w-[120px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="maximize">Maximize</SelectItem>
                          <SelectItem value="minimize">Minimize</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => removeMetric(metric.name)}
                        data-testid={`button-remove-metric-${metric.name}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
