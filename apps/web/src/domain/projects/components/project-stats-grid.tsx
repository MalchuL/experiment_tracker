import { StatCard } from "@/components/shared/stat-card";
import { FolderKanban, FlaskConical, Lightbulb, TrendingUp } from "lucide-react";
import type { DashboardStats } from "../types";

interface ProjectStatsGridProps {
  stats: DashboardStats | undefined;
}

export function ProjectStatsGrid({ stats }: ProjectStatsGridProps) {
  return (
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
        value={
          stats?.totalExperiments
            ? `${Math.round(
                ((stats?.completedExperiments ?? 0) / stats.totalExperiments) *
                  100
              )}%`
            : "0%"
        }
        icon={TrendingUp}
        description="Completed experiments"
      />
    </div>
  );
}


