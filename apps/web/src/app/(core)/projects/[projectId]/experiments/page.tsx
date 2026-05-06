"use client";

import { useEffect, useRef } from "react";
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
    useMissingParentExperimentNames,
} from "@/domain/experiments/hooks";
import { CreateExperimentDialog, ExperimentsTable } from "@/domain/experiments/components";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import { getDisplayedTrackedMetrics } from "@/lib/metrics/format-metric-label";

export default function Experiments() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const {
    experiments,
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    paginationMode: "scroll",
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
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const filteredMetrics = !project?.metrics
    ? []
    : getDisplayedTrackedMetrics(
        project.metrics.trackedMetrics,
        project.metrics.displayMetrics
      );

  const parentNamesById = useMissingParentExperimentNames(projectId, experiments);

  const isLoading = projectLoading || experimentsLoading || metricsLoading;
  const isRefreshing = experimentsFetching || metricsFetching;
  const handleRefresh = () => {
    void Promise.all([refetchExperiments(), refetchMetrics()]);
  };

  useEffect(() => {
    const node = loadMoreRef.current;
    if (!node || !hasNextPage) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry?.isIntersecting && hasNextPage && !experimentsFetchingNextPage) {
          void fetchNextPage();
        }
      },
      {
        root: null,
        rootMargin: "200px 0px",
        threshold: 0,
      }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [experimentsFetchingNextPage, fetchNextPage, hasNextPage, experiments.length]);

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
      <div className="space-y-6 px-6 pt-6">
        <PageHeader title="Experiments" description="Loading..." />
        <ListSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full min-w-0 gap-0">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-6 pt-6 pb-6">
        <div className="flex min-h-0 flex-1 flex-col space-y-6">
          <PageHeader
            title="Experiments"
            description={`Experiments for "${project?.name}". Shown newest first. Drag rows to update saved order.`}
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

          <div className="min-h-0 flex-1 overflow-y-auto">
            {!experiments.length ? (
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
                          <Plus className="mr-2 h-4 w-4" />
                          Create Experiment
                        </Button>
                      }
                    />
                  ) : null
                }
              />
            ) : (
              <>
                <ExperimentsTable
                  experiments={experiments}
                  projectMetrics={filteredMetrics}
                  aggregatedMetrics={aggregatedMetricsByExperiment}
                  parentNamesById={parentNamesById}
                  selectedExperimentId={selectedExperimentId}
                  onExperimentClick={setSelectedExperimentId}
                  onReorder={reorderExperiments}
                />
                <div ref={loadMoreRef} className="h-4" aria-hidden="true" />
                {(experimentsFetchingNextPage || hasNextPage) && (
                  <p className="text-sm text-muted-foreground">
                    {experimentsFetchingNextPage
                      ? "Loading more experiments..."
                      : "Scroll down to load more experiments."}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="push"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={
            aggregatedMetricsByExperiment?.[selectedExperimentId] || undefined
          }
        />
      ) : null}
    </div>
  );
}
