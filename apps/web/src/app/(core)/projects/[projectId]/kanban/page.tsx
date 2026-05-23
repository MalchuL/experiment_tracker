"use client";

import { useCallback } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { AlertCircle, FlaskConical, RefreshCw, Loader2 } from "lucide-react";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useExperiments, useAggregatedMetrics, useUpdateExperimentStatus } from "@/domain/experiments/hooks";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { KanbanBoard } from "@/domain/experiments/components";
import { ExperimentStatusType } from "@/domain/experiments/types";
import { useToast } from "@/lib/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import { getDisplayedTrackedMetrics } from "@/lib/metrics/format-metric-label";

export default function Kanban() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } =
    useSelectedExperimentStore();
  const {
    experiments,
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    hasNextPage: experimentsHasNextPage,
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
  const filteredMetrics = !project?.metrics
    ? []
    : getDisplayedTrackedMetrics(
        project.metrics.trackedMetrics,
        project.metrics.displayMetrics
      );

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
  const experimentsStillPaging =
    Boolean(experimentsHasNextPage) &&
    (experimentsFetchingNextPage || experimentsFetching) &&
    !experimentsLoading;
  const handleRefresh = () => {
    void Promise.all([refetchExperiments(), refetchMetrics()]);
  };

  if (!projectId) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4">
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
      <div className="space-y-6 px-6 pt-6">
        <PageHeader
          title="Kanban View"
          description="Drag experiments between columns to update status"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 gap-0">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-6 pt-6 pb-6">
        <PageHeader
          title="Kanban View"
          description={`Kanban board for "${project?.name}"`}
          actions={
            <div className="flex items-center gap-2">
              {experimentsStillPaging ? (
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-md border bg-background"
                  title="Loading more experiments…"
                  aria-label="Loading more experiments"
                >
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : null}
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
            </div>
          }
        />

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
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
            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              <KanbanBoard
                experiments={experiments}
                selectedExperimentId={selectedExperimentId}
                onExperimentClick={setSelectedExperimentId}
                onStatusUpdate={handleStatusUpdate}
              />
            </div>
          )}
        </div>
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="push"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetricsByExperiment={aggregatedMetricsByExperiment}
        />
      ) : null}
    </div>
  );
}
