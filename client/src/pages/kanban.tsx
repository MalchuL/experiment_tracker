import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { FlaskConical, Plus, Clock, Play, CheckCircle2, XCircle } from "lucide-react";
import type { Experiment } from "@shared/schema";
import { ExperimentStatus } from "@shared/schema";

const columns = [
  {
    id: ExperimentStatus.PLANNED,
    title: "Planned",
    icon: Clock,
    className: "bg-muted/50",
  },
  {
    id: ExperimentStatus.RUNNING,
    title: "Running",
    icon: Play,
    className: "bg-blue-500/10",
  },
  {
    id: ExperimentStatus.COMPLETE,
    title: "Complete",
    icon: CheckCircle2,
    className: "bg-green-500/10",
  },
  {
    id: ExperimentStatus.FAILED,
    title: "Failed",
    icon: XCircle,
    className: "bg-red-500/10",
  },
];

export default function Kanban() {
  const { data: experiments, isLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/experiments"],
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Kanban View" 
          description="Visualize experiment status across stages" 
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  if (!experiments || experiments.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Kanban View" 
          description="Visualize experiment status across stages" 
        />
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description="Create experiments to see them organized by status in the Kanban view."
          action={
            <Link href="/experiments">
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Create Experiment
              </Button>
            </Link>
          }
        />
      </div>
    );
  }

  const getExperimentsByStatus = (status: string) => {
    return experiments.filter(e => e.status === status);
  };

  return (
    <div className="space-y-6 h-full">
      <PageHeader
        title="Kanban View"
        description="Visualize experiment status across stages"
        actions={
          <Link href="/experiments">
            <Button data-testid="button-new-experiment">
              <Plus className="w-4 h-4 mr-2" />
              New Experiment
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                  <div className="space-y-2 pr-2">
                    {columnExperiments.length === 0 ? (
                      <div className="text-center py-8 text-sm text-muted-foreground">
                        No experiments
                      </div>
                    ) : (
                      columnExperiments.map((experiment) => (
                        <Link 
                          key={experiment.id} 
                          href={`/experiments/${experiment.id}`}
                        >
                          <Card 
                            className="hover-elevate active-elevate-2 cursor-pointer"
                            data-testid={`kanban-card-${experiment.id}`}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-start gap-2">
                                <div className="flex items-center justify-center w-7 h-7 rounded bg-accent flex-shrink-0">
                                  <FlaskConical className="w-3.5 h-3.5 text-accent-foreground" />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <p className="text-sm font-medium truncate">
                                    {experiment.name}
                                  </p>
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
                        </Link>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
