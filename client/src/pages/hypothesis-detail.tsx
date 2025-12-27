import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, Link } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { DetailSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  Lightbulb, 
  FlaskConical, 
  Calendar, 
  User,
  Target,
  TrendingUp
} from "lucide-react";
import { format } from "date-fns";
import type { Hypothesis, Experiment, Project } from "@shared/schema";

export default function HypothesisDetail() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();

  const { data: hypothesis, isLoading: hypothesisLoading } = useQuery<Hypothesis>({
    queryKey: ["/api/hypotheses", id],
  });

  const { data: linkedExperiments, isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/hypotheses", id, "experiments"],
  });

  const { data: project } = useQuery<Project>({
    queryKey: ["/api/projects", hypothesis?.projectId],
    enabled: !!hypothesis?.projectId,
  });

  const updateStatusMutation = useMutation({
    mutationFn: async (status: string) => {
      return apiRequest("PATCH", `/api/hypotheses/${id}`, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/hypotheses", id] });
      queryClient.invalidateQueries({ queryKey: ["/api/hypotheses"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      toast({
        title: "Status updated",
        description: "Hypothesis status has been updated.",
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

  if (hypothesisLoading || experimentsLoading) {
    return <DetailSkeleton />;
  }

  if (!hypothesis) {
    return (
      <EmptyState
        icon={Lightbulb}
        title="Hypothesis not found"
        description="The hypothesis you're looking for doesn't exist."
        action={
          <Link href="/hypotheses">
            <Button>Back to Hypotheses</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/hypotheses">
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <PageHeader
            title={hypothesis.title}
            actions={
              <Select
                value={hypothesis.status}
                onValueChange={(value) => updateStatusMutation.mutate(value)}
              >
                <SelectTrigger className="w-36" data-testid="select-update-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="proposed">Proposed</SelectItem>
                  <SelectItem value="testing">Testing</SelectItem>
                  <SelectItem value="supported">Supported</SelectItem>
                  <SelectItem value="refuted">Refuted</SelectItem>
                  <SelectItem value="inconclusive">Inconclusive</SelectItem>
                </SelectContent>
              </Select>
            }
          />
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={hypothesis.status} />
        {project && (
          <Link href={`/projects/${project.id}`}>
            <Badge variant="secondary" className="cursor-pointer">
              {project.name}
            </Badge>
          </Link>
        )}
      </div>

      {hypothesis.description && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm">{hypothesis.description}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <User className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Author</p>
                <p className="font-medium">{hypothesis.author}</p>
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
                <p className="font-medium">{format(new Date(hypothesis.createdAt), "MMM d, yyyy")}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <Target className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Baseline</p>
                <p className="font-medium capitalize">{hypothesis.baseline}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <FlaskConical className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Linked Experiments</p>
                <p className="font-medium">{linkedExperiments?.length || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {hypothesis.targetMetrics && hypothesis.targetMetrics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Target Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {hypothesis.targetMetrics.map((metric) => (
                <Badge key={metric} variant="secondary">
                  {metric}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-base">Linked Experiments</CardTitle>
        </CardHeader>
        <CardContent>
          {!linkedExperiments || linkedExperiments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No experiments linked to this hypothesis yet.
            </p>
          ) : (
            <div className="space-y-3">
              {linkedExperiments.map((experiment) => (
                <Link key={experiment.id} href={`/experiments/${experiment.id}`}>
                  <div 
                    className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                    data-testid={`linked-experiment-${experiment.id}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent">
                        <FlaskConical className="w-4 h-4 text-accent-foreground" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{experiment.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {experiment.id.slice(0, 8)}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={experiment.status} size="sm" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
