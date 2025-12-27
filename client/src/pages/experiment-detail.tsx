import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, Link } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { DetailSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { 
  ArrowLeft, 
  FlaskConical, 
  GitBranch, 
  Calendar, 
  Clock, 
  Play, 
  CheckCircle2, 
  XCircle,
  TrendingUp,
  TrendingDown
} from "lucide-react";
import { format } from "date-fns";
import type { Experiment, Metric, Project } from "@shared/schema";

export default function ExperimentDetail() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();

  const { data: experiment, isLoading: experimentLoading } = useQuery<Experiment>({
    queryKey: ["/api/experiments", id],
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery<Metric[]>({
    queryKey: ["/api/experiments", id, "metrics"],
  });

  const { data: project } = useQuery<Project>({
    queryKey: ["/api/projects", experiment?.projectId],
    enabled: !!experiment?.projectId,
  });

  const { data: parentExperiment } = useQuery<Experiment>({
    queryKey: ["/api/experiments", experiment?.parentExperimentId],
    enabled: !!experiment?.parentExperimentId,
  });

  const updateStatusMutation = useMutation({
    mutationFn: async (status: string) => {
      return apiRequest("PATCH", `/api/experiments/${id}`, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/experiments", id] });
      queryClient.invalidateQueries({ queryKey: ["/api/experiments"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
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
  });

  if (experimentLoading || metricsLoading) {
    return <DetailSkeleton />;
  }

  if (!experiment) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="Experiment not found"
        description="The experiment you're looking for doesn't exist."
        action={
          <Link href="/experiments">
            <Button>Back to Experiments</Button>
          </Link>
        }
      />
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="w-4 h-4" />;
      case "complete":
        return <CheckCircle2 className="w-4 h-4" />;
      case "failed":
        return <XCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/experiments">
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <PageHeader
            title={experiment.name}
            description={
              <span className="font-mono text-sm">{experiment.id}</span>
            }
            actions={
              <div className="flex items-center gap-2">
                <Select
                  value={experiment.status}
                  onValueChange={(value) => updateStatusMutation.mutate(value)}
                >
                  <SelectTrigger className="w-36" data-testid="select-update-status">
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
            }
          />
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={experiment.status} />
        {project && (
          <Link href={`/projects/${project.id}`}>
            <Badge variant="secondary" className="cursor-pointer">
              {project.name}
            </Badge>
          </Link>
        )}
        {experiment.parentExperimentId && parentExperiment && (
          <Link href={`/experiments/${parentExperiment.id}`}>
            <Badge variant="outline" className="cursor-pointer flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              from {parentExperiment.name}
            </Badge>
          </Link>
        )}
      </div>

      {experiment.status === "running" && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Progress</span>
              <span className="text-sm text-muted-foreground">{experiment.progress}%</span>
            </div>
            <Progress value={experiment.progress} className="h-2" />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                {getStatusIcon(experiment.status)}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="font-medium capitalize">{experiment.status}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <Calendar className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="font-medium">{format(new Date(experiment.createdAt), "MMM d, yyyy")}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <Clock className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Started</p>
                <p className="font-medium">
                  {experiment.startedAt 
                    ? format(new Date(experiment.startedAt), "MMM d, HH:mm") 
                    : "Not started"
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <CheckCircle2 className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="font-medium">
                  {experiment.completedAt 
                    ? format(new Date(experiment.completedAt), "MMM d, HH:mm") 
                    : "In progress"
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="features" className="space-y-4">
        <TabsList>
          <TabsTrigger value="features" data-testid="tab-features">Features</TabsTrigger>
          <TabsTrigger value="metrics" data-testid="tab-metrics">
            Metrics ({metrics?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="code" data-testid="tab-code">Code Diff</TabsTrigger>
        </TabsList>

        <TabsContent value="features" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Full Features</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-sm font-mono bg-muted p-4 rounded-md overflow-auto max-h-80">
                  {JSON.stringify(experiment.features, null, 2) || "No features defined"}
                </pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Features Diff</CardTitle>
              </CardHeader>
              <CardContent>
                {experiment.featuresDiff ? (
                  <pre className="text-sm font-mono bg-muted p-4 rounded-md overflow-auto max-h-80">
                    {JSON.stringify(experiment.featuresDiff, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No diff available (root experiment)
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          {!metrics || metrics.length === 0 ? (
            <EmptyState
              icon={TrendingUp}
              title="No metrics yet"
              description="Metrics will appear here once the experiment logs them."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {metrics.map((metric) => (
                <Card key={metric.id} data-testid={`metric-card-${metric.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">{metric.name}</p>
                        <p className="text-2xl font-bold font-mono">
                          {metric.value.toFixed(4)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        {metric.direction === "minimize" ? (
                          <TrendingDown className="w-4 h-4 text-green-600" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-green-600" />
                        )}
                        <Badge variant="secondary" className="text-xs">
                          {metric.direction}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Step {metric.step}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="code" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Git Diff</CardTitle>
            </CardHeader>
            <CardContent>
              {experiment.gitDiff ? (
                <pre className="text-sm font-mono bg-muted p-4 rounded-md overflow-auto max-h-96 whitespace-pre-wrap">
                  {experiment.gitDiff}
                </pre>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No code diff captured for this experiment.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
