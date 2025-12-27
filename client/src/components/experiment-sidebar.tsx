import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import {
  X,
  GitBranch,
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  TrendingUp,
  TrendingDown,
  Save,
  Palette,
} from "lucide-react";
import { format } from "date-fns";
import type { Experiment, Metric, Project, ProjectMetric } from "@shared/schema";
import { EXPERIMENT_COLORS } from "@shared/schema";

interface ExperimentSidebarProps {
  experimentId: string | null;
  onClose: () => void;
  projectMetrics?: ProjectMetric[];
  aggregatedMetrics?: Record<string, number | null>;
}

export function ExperimentSidebar({
  experimentId,
  onClose,
  projectMetrics,
  aggregatedMetrics,
}: ExperimentSidebarProps) {
  const { toast } = useToast();
  const [editedName, setEditedName] = useState<string | null>(null);
  const [editedDescription, setEditedDescription] = useState<string | null>(null);
  const [editedColor, setEditedColor] = useState<string | null>(null);

  const { data: experiment, isLoading: experimentLoading } = useQuery<Experiment>({
    queryKey: ["/api/experiments", experimentId],
    enabled: !!experimentId,
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery<Metric[]>({
    queryKey: ["/api/experiments", experimentId, "metrics"],
    enabled: !!experimentId,
  });

  const { data: project } = useQuery<Project>({
    queryKey: ["/api/projects", experiment?.projectId],
    enabled: !!experiment?.projectId,
  });

  const { data: parentExperiment } = useQuery<Experiment>({
    queryKey: ["/api/experiments", experiment?.parentExperimentId],
    enabled: !!experiment?.parentExperimentId,
  });

  const updateMutation = useMutation({
    mutationFn: async (updates: Partial<Experiment>) => {
      return apiRequest("PATCH", `/api/experiments/${experimentId}`, updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments", experimentId] });
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({ queryKey: ["/api/projects", experiment?.projectId, "experiments"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      toast({
        title: "Experiment updated",
        description: "Changes have been saved.",
      });
      setEditedName(null);
      setEditedDescription(null);
      setEditedColor(null);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to update experiment.",
        variant: "destructive",
      });
    },
  });

  if (!experimentId) return null;

  const formatMetricValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "NaN";
    return value.toFixed(4);
  };

  const currentName = editedName !== null ? editedName : (experiment?.name || "");
  const currentDescription = editedDescription !== null ? editedDescription : (experiment?.description || "");
  const currentColor = editedColor !== null ? editedColor : (experiment?.color || EXPERIMENT_COLORS[0]);

  const hasChanges = 
    (editedName !== null && editedName !== (experiment?.name || "")) ||
    (editedDescription !== null && editedDescription !== (experiment?.description || "")) ||
    (editedColor !== null && editedColor !== experiment?.color);

  const saveChanges = () => {
    const updates: Partial<Experiment> = {};
    if (editedName !== null && editedName !== (experiment?.name || "")) {
      updates.name = editedName;
    }
    if (editedDescription !== null && editedDescription !== (experiment?.description || "")) {
      updates.description = editedDescription;
    }
    if (editedColor !== null && editedColor !== experiment?.color) {
      updates.color = editedColor;
    }
    if (Object.keys(updates).length > 0) {
      updateMutation.mutate(updates);
    }
  };

  return (
    <div
      className="fixed right-0 top-0 h-full w-96 bg-background border-l z-50 flex flex-col shadow-lg"
      data-testid="experiment-sidebar"
    >
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: currentColor }}
          />
          <h2 className="font-semibold truncate">
            {experimentLoading ? (
              <Skeleton className="h-5 w-32" />
            ) : (
              experiment?.name || "Experiment"
            )}
          </h2>
        </div>
        <div className="flex items-center gap-1">
          {hasChanges && (
            <Button
              size="sm"
              onClick={saveChanges}
              disabled={updateMutation.isPending}
              data-testid="button-save-experiment"
            >
              <Save className="w-4 h-4 mr-1" />
              Save
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            data-testid="button-close-sidebar"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {experimentLoading ? (
        <div className="p-4 space-y-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : experiment ? (
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={experiment.status} />
              {project && (
                <Badge variant="secondary">{project.name}</Badge>
              )}
              {experiment.parentExperimentId && parentExperiment && (
                <Badge variant="outline" className="flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  from {parentExperiment.name}
                </Badge>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={currentName}
                onChange={(e) => setEditedName(e.target.value)}
                placeholder="Experiment name"
                data-testid="input-name"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Select
                value={experiment.status}
                onValueChange={(value) => updateMutation.mutate({ status: value as Experiment["status"] })}
              >
                <SelectTrigger className="w-32 h-8" data-testid="select-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="planned">Planned</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="complete">Complete</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {experiment.status === "running" && (
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Progress</span>
                  <span>{experiment.progress}%</span>
                </div>
                <Progress value={experiment.progress} className="h-2" />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={currentDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                placeholder="Add experiment description..."
                className="min-h-[80px] resize-none"
                data-testid="input-description"
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Palette className="w-4 h-4" />
                Color
              </Label>
              <div className="flex gap-2 flex-wrap">
                {EXPERIMENT_COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-6 h-6 rounded-full border-2 transition-transform ${
                      currentColor === color
                        ? "border-foreground scale-110"
                        : "border-transparent hover:scale-105"
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setEditedColor(color)}
                    data-testid={`color-option-${color}`}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="p-2 rounded-md bg-muted/50">
                <p className="text-muted-foreground text-xs">Created</p>
                <p className="font-medium">
                  {format(new Date(experiment.createdAt), "MMM d, yyyy")}
                </p>
              </div>
              <div className="p-2 rounded-md bg-muted/50">
                <p className="text-muted-foreground text-xs">Started</p>
                <p className="font-medium">
                  {experiment.startedAt
                    ? format(new Date(experiment.startedAt), "MMM d, HH:mm")
                    : "-"}
                </p>
              </div>
            </div>

            <div className="text-xs font-mono text-muted-foreground p-2 bg-muted/50 rounded-md">
              ID: {experiment.id}
            </div>

            <Tabs defaultValue="metrics" className="space-y-2">
              <TabsList className="w-full">
                <TabsTrigger value="metrics" className="flex-1" data-testid="tab-metrics">
                  Metrics
                </TabsTrigger>
                <TabsTrigger value="features" className="flex-1" data-testid="tab-features">
                  Features
                </TabsTrigger>
                <TabsTrigger value="code" className="flex-1" data-testid="tab-code">
                  Code
                </TabsTrigger>
              </TabsList>

              <TabsContent value="metrics" className="space-y-2">
                {projectMetrics && projectMetrics.length > 0 ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Project Metrics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <div className="space-y-2">
                        {projectMetrics.map((pm) => {
                          const value = aggregatedMetrics?.[pm.name];
                          return (
                            <div
                              key={pm.name}
                              className="flex items-center justify-between text-sm"
                              data-testid={`metric-${pm.name}`}
                            >
                              <div className="flex items-center gap-2">
                                <span>{pm.name}</span>
                                {pm.direction === "minimize" ? (
                                  <TrendingDown className="w-3 h-3 text-muted-foreground" />
                                ) : (
                                  <TrendingUp className="w-3 h-3 text-muted-foreground" />
                                )}
                              </div>
                              <span
                                className={`font-mono ${
                                  value === null || value === undefined
                                    ? "text-muted-foreground"
                                    : ""
                                }`}
                              >
                                {formatMetricValue(value)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                ) : null}

                {metricsLoading ? (
                  <Skeleton className="h-24 w-full" />
                ) : metrics && metrics.length > 0 ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Logged Metrics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <div className="space-y-2">
                        {metrics.map((metric) => (
                          <div
                            key={metric.id}
                            className="flex items-center justify-between text-sm"
                            data-testid={`logged-metric-${metric.id}`}
                          >
                            <div className="flex items-center gap-2">
                              <span>{metric.name}</span>
                              <Badge variant="outline" className="text-xs">
                                step {metric.step}
                              </Badge>
                            </div>
                            <span className="font-mono">
                              {metric.value.toFixed(4)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No metrics logged yet
                  </p>
                )}
              </TabsContent>

              <TabsContent value="features" className="space-y-2">
                <Card>
                  <CardHeader className="py-2 px-3">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Full Features
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-3 pb-3 pt-0">
                    <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-32">
                      {JSON.stringify(experiment.features, null, 2) ||
                        "No features"}
                    </pre>
                  </CardContent>
                </Card>

                {experiment.featuresDiff && (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Features Diff
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(experiment.featuresDiff, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="code" className="space-y-2">
                {experiment.gitDiff ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Git Diff
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-48 whitespace-pre-wrap">
                        {experiment.gitDiff}
                      </pre>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No code diff captured
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      ) : (
        <div className="p-4 text-center text-muted-foreground">
          Experiment not found
        </div>
      )}
    </div>
  );
}
