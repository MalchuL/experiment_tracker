"use client";

import { useMemo, useCallback } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { AlertCircle, FlaskConical, RefreshCw } from "lucide-react";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useExperiments, useAggregatedMetrics, useUpdateExperimentStatus } from "@/domain/experiments/hooks";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { KanbanBoard } from "@/domain/experiments/components";
import { ExperimentStatusType } from "@/domain/experiments/types";
import { useToast } from "@/lib/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";

export default function Kanban() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } =
    useSelectedExperimentStore();
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
  const { updateStatus } = useUpdateExperimentStatus(projectId);
  const { toast } = useToast();
  // Filter metrics by displayMetrics setting
  const filteredMetrics = useMemo(() => {
    if (!project?.metrics) return [];
    const displayMetrics = project?.settings?.displayMetrics || [];
    if (displayMetrics.length === 0) return project.metrics;
    return project.metrics.filter((m) => displayMetrics.includes(m.name));
  }, [project?.metrics, project?.settings?.displayMetrics]);

  const handleStatusUpdate = useCallback(
    (experimentId: string, status: ExperimentStatusType) => {
      updateStatus(experimentId, status, {
        onSuccess: () => {
          toast({
            title: "Status updated",
            description: "Experiment moved to new column.",
          });
        },
        onError: () => {
          toast({
            title: "Error",
            description: "Failed to update experiment status.",
            variant: "destructive",
          });
        },
      });
    },
    [updateStatus, toast]
  );

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
          Click on the logo in the sidebar to select a project and view its
          Kanban board.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Kanban View"
          description="Drag experiments between columns to update status"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      <PageHeader
        title="Kanban View"
        description={`Kanban board for "${project?.name}"`}
        actions={
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            data-testid="button-refresh-kanban"
            aria-label="Refresh kanban"
          >
            <RefreshCw className={isRefreshing ? "animate-spin" : ""} />
          </Button>
        }
      />

      {experiments.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description={
            projectId
              ? "No experiments in this project."
              : "Create experiments to organize them by status."
          }
        />
      ) : (
        <KanbanBoard
          experiments={experiments}
          onExperimentClick={setSelectedExperimentId}
          onStatusUpdate={handleStatusUpdate}
        />
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={
            aggregatedMetricsByExperiment?.[selectedExperimentId] || undefined
          }
        />
      )}
    </div>
  );
}
