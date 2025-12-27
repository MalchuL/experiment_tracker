import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { DetailSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, FlaskConical, Lightbulb, Plus, Calendar, User } from "lucide-react";
import { format } from "date-fns";
import type { Project, Experiment, Hypothesis } from "@shared/schema";

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: project, isLoading: projectLoading } = useQuery<Project>({
    queryKey: ["/api/projects", id],
  });

  const { data: experiments, isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/projects", id, "experiments"],
  });

  const { data: hypotheses, isLoading: hypothesesLoading } = useQuery<Hypothesis[]>({
    queryKey: ["/api/projects", id, "hypotheses"],
  });

  if (projectLoading || experimentsLoading || hypothesesLoading) {
    return <DetailSkeleton />;
  }

  if (!project) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="Project not found"
        description="The project you're looking for doesn't exist."
        action={
          <Link href="/projects">
            <Button>Back to Projects</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/projects">
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <PageHeader
          title={project.name}
          description={project.description || "No description"}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-accent">
                <User className="w-5 h-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Owner</p>
                <p className="font-medium">{project.owner}</p>
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
                <p className="text-sm text-muted-foreground">Experiments</p>
                <p className="font-medium">{project.experimentCount}</p>
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
                <p className="font-medium">{format(new Date(project.createdAt), "MMM d, yyyy")}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="experiments" className="space-y-4">
        <TabsList>
          <TabsTrigger value="experiments" data-testid="tab-experiments">
            Experiments ({experiments?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="hypotheses" data-testid="tab-hypotheses">
            Hypotheses ({hypotheses?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="experiments" className="space-y-4">
          <div className="flex justify-end">
            <Link href={`/experiments/new?projectId=${id}`}>
              <Button data-testid="button-new-experiment">
                <Plus className="w-4 h-4 mr-2" />
                New Experiment
              </Button>
            </Link>
          </div>
          
          {!experiments || experiments.length === 0 ? (
            <EmptyState
              icon={FlaskConical}
              title="No experiments yet"
              description="Create your first experiment to start testing hypotheses."
              action={
                <Link href={`/experiments/new?projectId=${id}`}>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Experiment
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {experiments.map((experiment) => (
                <Link key={experiment.id} href={`/experiments/${experiment.id}`}>
                  <Card 
                    className="hover-elevate active-elevate-2 cursor-pointer"
                    data-testid={`experiment-card-${experiment.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex items-center justify-center w-10 h-10 rounded-md bg-accent">
                            <FlaskConical className="w-5 h-5 text-accent-foreground" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium truncate">{experiment.name}</p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {experiment.id.slice(0, 8)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={experiment.status} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="hypotheses" className="space-y-4">
          <div className="flex justify-end">
            <Link href={`/hypotheses/new?projectId=${id}`}>
              <Button data-testid="button-new-hypothesis">
                <Plus className="w-4 h-4 mr-2" />
                New Hypothesis
              </Button>
            </Link>
          </div>
          
          {!hypotheses || hypotheses.length === 0 ? (
            <EmptyState
              icon={Lightbulb}
              title="No hypotheses yet"
              description="Create hypotheses to track your research claims."
              action={
                <Link href={`/hypotheses/new?projectId=${id}`}>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Hypothesis
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {hypotheses.map((hypothesis) => (
                <Link key={hypothesis.id} href={`/hypotheses/${hypothesis.id}`}>
                  <Card 
                    className="hover-elevate active-elevate-2 cursor-pointer"
                    data-testid={`hypothesis-card-${hypothesis.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex items-center justify-center w-10 h-10 rounded-md bg-accent">
                            <Lightbulb className="w-5 h-5 text-accent-foreground" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium truncate">{hypothesis.title}</p>
                            <p className="text-xs text-muted-foreground">
                              By {hypothesis.author}
                            </p>
                          </div>
                        </div>
                        <StatusBadge status={hypothesis.status} />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
