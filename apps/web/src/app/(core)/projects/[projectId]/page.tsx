"use client";

import { PageHeader } from "@/components/shared/page-header";
import { EntityIdDisplay } from "@/components/shared/entity-id-display";
import { DashboardSkeleton } from "@/components/shared/loading-skeleton";
import { ProjectStatsGrid } from "@/domain/projects/components/project-stats-grid";
import { RecentExperimentsCard } from "@/domain/projects/components/recent-experiments-card";
import { RecentHypothesesCard } from "@/domain/projects/components/recent-hypotheses-card";
import { ExperimentStatusCards } from "@/domain/projects/components/experiment-status-cards";
import { useStats } from "@/domain/projects/hooks";
import { useRecentExperiments } from "@/domain/experiments/hooks";
import { useRecentHypothesis } from "@/domain/hypothesis/hooks";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useParams } from "next/navigation";

export default function ProjectDashboard() {
  const { projectId: routeProjectId } = useParams<{ projectId: string }>();
  const { project, isLoading } = useCurrentProject();

  const projectId = project?.id;
  const { stats, statsIsLoading } = useStats(projectId);

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
      <div className="space-y-3">
        <PageHeader
          title={project?.name ?? "Overview"}
          description="Overview of your research experiments and hypotheses"
        />
        {project ? <EntityIdDisplay label="ID" value={project.id} /> : null}
      </div>

      <ProjectStatsGrid stats={stats} />

      <div className="grid gap-4 lg:grid-cols-7">
        <RecentExperimentsCard
          experiments={recentExperiments}
          projectId={routeProjectId}
        />
        <RecentHypothesesCard hypotheses={recentHypotheses} />
      </div>

      <ExperimentStatusCards stats={stats} />
    </div>
  );
}
