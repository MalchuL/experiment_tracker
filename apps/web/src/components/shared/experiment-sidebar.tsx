import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/shared/status-badge";
import { ExperimentEditForm } from "@/components/shared/experiment-edit-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/lib/hooks/use-toast";
import { useExperiment } from "@/domain/experiments/hooks/experiment-hook";
import {
  X,
  GitBranch,
  TrendingUp,
  TrendingDown,
  RefreshCw,
} from "lucide-react";
import { format } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type { Metric } from "@/domain/metrics/types";
import type { Project, ProjectMetric } from "@/domain/projects/types";
import { useExperimentMetrics } from "@/domain/metrics/hooks";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { REFRESH_EXPERIMENT_SIDEBAR_INTERVAL } from "@/lib/constants/rates";

interface ExperimentSidebarProps {
  experimentId: string | null;
  onClose: () => void;
  projectMetrics?: ProjectMetric[];
  aggregatedMetrics?: Metric[];
}

export function ExperimentSidebar({
  experimentId,
  onClose,
  projectMetrics,
  aggregatedMetrics,
}: ExperimentSidebarProps) {
  const { toast } = useToast();

  const {
    experiment,
    isLoading: experimentLoading,
    isFetching: experimentFetching,
    updateIsPending,
    updateExperiment,
    refetch,
  } = useExperiment(experimentId || "", { refetchInterval: REFRESH_EXPERIMENT_SIDEBAR_INTERVAL });

  const { metrics, isLoading: metricsLoading } = useExperimentMetrics(experimentId || "");
  const { project } = useProject(experiment?.projectId);

  const { experiment: parentExperiment } = useExperiment(experiment?.parentExperimentId || "");

  const handleSaveForm = async (data: { name: string; description: string; color: string }) => {
    if (!experiment) return;
    try {
      await updateExperiment(
        {
          name: data.name,
          description: data.description,
          color: data.color,
        },
        {
          onSuccess: () => {
            toast({
              title: "Experiment updated",
              description: "Changes have been saved.",
            });
          },
          onError: () => {
            toast({
              title: "Error",
              description: "Failed to update experiment.",
              variant: "destructive",
            });
          },
        }
      );
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update experiment.",
        variant: "destructive",
      });
    }
  };

  const handleStatusChange = async (status: Experiment["status"]) => {
    if (!experiment) return;
    try {
      await updateExperiment(
        {
          status,
        },
        {
          onSuccess: () => {
            toast({
              title: "Status updated",
              description: "Experiment status has been updated.",
            });
          },
          onError: () => {
            toast({
              title: "Error",
              description: "Failed to update status.",
              variant: "destructive",
            });
          },
        }
      );
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update status.",
        variant: "destructive",
      });
    }
  };

  if (!experimentId) return null;

  const formatMetricValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "NaN";
    return value.toFixed(4);
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
            style={{ backgroundColor: experiment?.color || "#3b82f6" }}
          />
          <h2 className="font-semibold truncate">
            {experimentLoading ? (
              <Skeleton className="h-5 w-32" />
            ) : (
              experiment?.name || "Experiment"
            )}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            disabled={experimentFetching || !experimentId}
            data-testid="button-refresh-experiment"
            aria-label="Refresh experiment"
          >
            <RefreshCw
              className={`w-4 h-4 ${experimentFetching ? "animate-spin" : ""}`}
            />
          </Button>
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

            <ExperimentEditForm
              experiment={experiment}
              onSave={handleSaveForm}
              isSaving={updateIsPending}
            />

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Select
                value={experiment.status}
                onValueChange={(value) => handleStatusChange(value as Experiment["status"])}
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
                          const value = aggregatedMetrics?.find((m) => m.name === pm.name)?.value;
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
