"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DashboardSkeleton } from "@/components/shared/loading-skeleton";
import { ProjectStatsGrid } from "@/domain/projects/components/project-stats-grid";
import { RecentExperimentsCard } from "@/domain/projects/components/recent-experiments-card";
import { RecentHypothesesCard } from "@/domain/projects/components/recent-hypotheses-card";
import { ExperimentStatusCards } from "@/domain/projects/components/experiment-status-cards";
import { useStats } from "@/domain/projects/hooks/stats-hook";
import { useRecentExperiments } from "@/domain/experiments/hooks/recent-experiments";
import { useRecentHypothesis } from "@/domain/hypothesis/hooks/recent-hypothesis";
import { useCurrentProject } from "@/domain/projects/hooks/project-provider";

export default function ProjectDashboard() {
  const { project, isLoading } = useCurrentProject();

  const projectId = project?.id;
  const { stats, statsIsLoading } = useStats();

  const { experiments: recentExperiments, recentExperimentsIsLoading: experimentsLoading } = useRecentExperiments(projectId);

  const { hypotheses: recentHypotheses, recentHypothesesIsLoading: hypothesesLoading } = useRecentHypothesis(projectId);


  if (isLoading) {
    return <DashboardSkeleton />;
  }
  if (statsIsLoading || experimentsLoading || hypothesesLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your research experiments and hypotheses"
      />

      <ProjectStatsGrid stats={stats} />

      <div className="grid gap-4 lg:grid-cols-7">
        <RecentExperimentsCard experiments={recentExperiments} />
        <RecentHypothesesCard hypotheses={recentHypotheses} />
      </div>

      <ExperimentStatusCards stats={stats} />
    </div>
  );
}
