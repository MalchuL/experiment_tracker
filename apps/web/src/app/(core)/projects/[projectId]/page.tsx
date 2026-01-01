"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardSkeleton } from "@/domain/projects/components/loading-skeleton";
import { 
  FolderKanban, 
  FlaskConical, 
  Lightbulb, 
  CheckCircle2, 
  XCircle, 
  Play,
  TrendingUp,
  Clock
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { useStats } from "@/domain/projects/hooks/stats-hook";
import { useRecentExperiments } from "@/domain/experiments/hooks/recent-experiments";
import { useRecentHypothesis } from "@/domain/hypothesis/hooks/recent-hypothesis";

export default function ProjectDashboard() {
  const { projectId } = useParams<{ projectId: string }>();
  const { project } = useProject(projectId);

  const { stats, statsIsLoading } = useStats();

  const { experiments: recentExperiments, recentExperimentsIsLoading: experimentsLoading } = useRecentExperiments(projectId);

  const { hypotheses: recentHypotheses, recentHypothesesIsLoading: hypothesesLoading } = useRecentHypothesis(projectId);

  if (statsIsLoading || experimentsLoading || hypothesesLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your research experiments and hypotheses"
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Projects"
          value={stats?.totalProjects ?? 0}
          icon={FolderKanban}
          description="Active research directions"
        />
        <StatCard
          title="Experiments"
          value={stats?.totalExperiments ?? 0}
          icon={FlaskConical}
          description={`${stats?.runningExperiments ?? 0} currently running`}
        />
        <StatCard
          title="Hypotheses"
          value={stats?.totalHypotheses ?? 0}
          icon={Lightbulb}
          description={`${stats?.supportedHypotheses ?? 0} supported`}
        />
        <StatCard
          title="Success Rate"
          value={stats?.totalExperiments ? 
            `${Math.round(((stats?.completedExperiments ?? 0) / stats.totalExperiments) * 100)}%` : 
            "0%"
          }
          icon={TrendingUp}
          description="Completed experiments"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-7">
        <Card className="lg:col-span-4">
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="text-lg font-medium">Recent Experiments</CardTitle>
            <Link href="/experiments">
              <span className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                View all
              </span>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(!recentExperiments || recentExperiments.length === 0) ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No experiments yet. Create your first experiment to get started.
                </p>
              ) : (
                recentExperiments.slice(0, 5).map((experiment) => (
                  <Link key={experiment.id} href={`/experiments/${experiment.id}`}>
                    <div 
                      className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                      data-testid={`experiment-row-${experiment.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent">
                          <FlaskConical className="w-4 h-4 text-accent-foreground" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{experiment.name}</p>
                          <p className="text-xs text-muted-foreground font-mono truncate">
                            {experiment.id.slice(0, 8)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusBadge status={experiment.status} size="sm" />
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="text-lg font-medium">Hypothesis Status</CardTitle>
            <Link href="/hypotheses">
              <span className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                View all
              </span>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(!recentHypotheses || recentHypotheses.length === 0) ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No hypotheses yet. Create your first hypothesis to track research claims.
                </p>
              ) : (
                recentHypotheses.slice(0, 5).map((hypothesis) => (
                  <Link key={hypothesis.id} href={`/hypotheses/${hypothesis.id}`}>
                    <div 
                      className="flex items-center justify-between gap-4 p-3 rounded-md hover-elevate active-elevate-2 cursor-pointer"
                      data-testid={`hypothesis-row-${hypothesis.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent">
                          <Lightbulb className="w-4 h-4 text-accent-foreground" />
                        </div>
                        <p className="text-sm font-medium truncate">{hypothesis.title}</p>
                      </div>
                      <StatusBadge status={hypothesis.status} size="sm" />
                    </div>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="hover-elevate">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-500/15">
                <Play className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats?.runningExperiments ?? 0}</p>
                <p className="text-sm text-muted-foreground">Running</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover-elevate">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-green-500/15">
                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats?.completedExperiments ?? 0}</p>
                <p className="text-sm text-muted-foreground">Completed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover-elevate">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-500/15">
                <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats?.failedExperiments ?? 0}</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
