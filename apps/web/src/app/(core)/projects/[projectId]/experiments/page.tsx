"use client";

import { useMemo } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { Button } from "@/components/ui/button";
import { useCurrentProject } from "@/domain/projects/hooks";
import { Plus, FlaskConical, AlertCircle, RefreshCw } from "lucide-react";
import {
    useExperiments,
    useReorderExperiments,
    useAggregatedMetrics,
} from "@/domain/experiments/hooks";
import { CreateExperimentDialog, ExperimentsTable } from "@/domain/experiments/components";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";

export default function Experiments() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const {
    experiments,
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });
  const {
    aggregatedMetricsByExperiment,
    isFetching: metricsFetching,
    isLoading: metricsLoading,
    refetch: refetchMetrics,
  } = useAggregatedMetrics(projectId, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });
  const { reorderExperiments } = useReorderExperiments(projectId);

  // Filter metrics by displayMetrics setting
  const filteredMetrics = useMemo(() => {
    if (!project?.metrics) return [];
    const displayMetrics = project?.settings?.displayMetrics || [];
    if (displayMetrics.length === 0) return project.metrics;
    return project.metrics.filter(m => displayMetrics.includes(m.name));
  }, [project?.metrics, project?.settings?.displayMetrics]);

  const sortedExperiments = useMemo(() => {
    if (!experiments) return [];
    return [...experiments].sort((a, b) => a.order - b.order);
  }, [experiments]);

  const isLoading = projectLoading || experimentsLoading || metricsLoading;
  const isRefreshing = experimentsFetching || metricsFetching;
  const handleRefresh = () => {
    void Promise.all([refetchExperiments(), refetchMetrics()]);
  };

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its experiments.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Experiments" description="Loading..." />
        <ListSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description={`Experiments for "${project?.name}". Drag to reorder.`}
        actions={
          projectId ? (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={handleRefresh}
                disabled={isRefreshing}
                data-testid="button-refresh-experiments"
                aria-label="Refresh experiments"
              >
                <RefreshCw className={isRefreshing ? "animate-spin" : ""} />
              </Button>
              <CreateExperimentDialog
                projectId={projectId}
                projectName={project?.name}
              />
            </div>
          ) : null
        }
      />

      {!sortedExperiments.length ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description="Create your first experiment to start tracking your research runs."
          action={
            projectId ? (
              <CreateExperimentDialog
                projectId={projectId}
                projectName={project?.name}
                trigger={
                  <Button data-testid="button-empty-create-experiment">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Experiment
                  </Button>
                }
              />
            ) : null
          }
        />
      ) : (
        <ExperimentsTable
          experiments={sortedExperiments}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={aggregatedMetricsByExperiment}
          onExperimentClick={setSelectedExperimentId}
          onReorder={reorderExperiments}
        />
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={aggregatedMetricsByExperiment?.[selectedExperimentId] || undefined}
        />
      )}
    </div>
  );
}
