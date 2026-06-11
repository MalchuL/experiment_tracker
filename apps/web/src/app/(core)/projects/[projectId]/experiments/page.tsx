"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCurrentProject } from "@/domain/projects/hooks";
import { Plus, FlaskConical, AlertCircle, RefreshCw } from "lucide-react";
import {
  useExperiments,
  useReorderExperiments,
  useSelectiveProjectMetrics,
  useTopProjectMetrics,
  useMissingParentExperimentNames,
} from "@/domain/experiments/hooks";
import { CreateExperimentDialog, ExperimentsTable } from "@/domain/experiments/components";
import { ExperimentCompareBar } from "@/domain/experiments/components/experiment-compare-bar";
import {
  loadExperimentsTablePinLead,
  saveExperimentsTablePinLead,
} from "@/domain/experiments/lib/experiments-table-column-widths";
import { useOrderedExperimentSelection } from "@/domain/experiments/hooks";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import { getDisplayedTrackedMetrics } from "@/lib/metrics/format-metric-label";
import { ProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { Switch } from "@/components/ui/switch";
import { CompareLabeledSwitch } from "@/domain/compare/components/compare-labeled-switch";

export default function Experiments() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [pinLeadColumns, setPinLeadColumns] = useState(true);
  const [experimentsListReady, setExperimentsListReady] = useState(false);
  const {
    selectionMode,
    setSelectionMode,
    orderedIds,
    toggleExperiment,
    getOrderNumber,
  } = useOrderedExperimentSelection();

  const {
    experiments,
    total,
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    paginationMode: "scroll",
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
    search: searchQuery,
  });

  useEffect(() => {
    setExperimentsListReady(false);
  }, [projectId]);

  useEffect(() => {
    if (projectId && !experimentsLoading) {
      setExperimentsListReady(true);
    }
  }, [projectId, experimentsLoading]);

  useEffect(() => {
    if (projectId) {
      setPinLeadColumns(loadExperimentsTablePinLead(projectId));
    }
  }, [projectId]);

  const { reorderExperiments } = useReorderExperiments(projectId);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const experimentsListScrollRef = useRef<HTMLDivElement | null>(null);

  const filteredMetrics = !project?.metrics
    ? []
    : getDisplayedTrackedMetrics(
        project.metrics.trackedMetrics,
        project.metrics.displayMetrics
      );

  const experimentIds = useMemo(() => experiments.map((experiment) => experiment.id), [experiments]);
  const {
    metricsByExperiment,
    isFetching: metricsFetching,
    isLoading: metricsLoading,
    refetch: refetchMetrics,
  } = useSelectiveProjectMetrics(projectId, experimentIds, filteredMetrics, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });
  const {
    topMetrics,
    isFetching: topMetricsFetching,
    refetch: refetchTopMetrics,
  } = useTopProjectMetrics(projectId, filteredMetrics, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });

  const parentNamesById = useMissingParentExperimentNames(projectId, experiments);

  const loadedExperimentNameById = useMemo(() => {
    const out: Record<string, string> = {};
    for (const e of experiments) {
      out[e.id] = e.name;
    }
    return out;
  }, [experiments]);

  const searchTrimmed = searchQuery.trim();
  const reorderDisabled = searchTrimmed.length > 0;

  const showInitialPageSkeleton =
    projectLoading ||
    (Boolean(projectId) &&
      !experimentsListReady &&
      (experimentsLoading || metricsLoading));

  const isRefreshing = experimentsFetching || metricsFetching || topMetricsFetching;
  const handleRefresh = () => {
    const refetches: Promise<unknown>[] = [refetchExperiments()];
    if (filteredMetrics.length > 0) {
      refetches.push(refetchMetrics(), refetchTopMetrics());
    }
    void Promise.all(refetches);
  };

  useEffect(() => {
    const root = experimentsListScrollRef.current;
    const node = loadMoreRef.current;
    if (!node || !hasNextPage || !root) {
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
        root,
        rootMargin: "200px 0px",
        threshold: 0,
      }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [experimentsFetchingNextPage, fetchNextPage, hasNextPage, experiments.length]);

  if (!projectId) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its experiments.
        </p>
      </div>
    );
  }

  if (showInitialPageSkeleton) {
    return (
      <div className="space-y-6 px-6 pt-6">
        <PageHeader title="Experiments" description="Loading..." />
        <ListSkeleton count={5} />
      </div>
    );
  }

  const showEmptyProject = !searchTrimmed && experiments.length === 0;
  const showNoSearchMatches =
    Boolean(searchTrimmed) && !experimentsFetching && experiments.length === 0;

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 gap-0">
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-6 pt-6 pb-6">
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

          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-1.5 sm:max-w-md">
              <Label htmlFor="experiments-search">Search id, name, description, or tags</Label>
              <Input
                id="experiments-search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. uuid fragment, baseline, gpu-a100…"
                data-testid="input-experiments-search"
              />
            </div>
            <div className="flex h-10 shrink-0 flex-wrap items-center gap-4">
              <CompareLabeledSwitch
                id="experiments-selection-mode"
                label="Selection mode"
                checked={selectionMode}
                onCheckedChange={setSelectionMode}
                tip="Pick experiments in order; #1 is the compare baseline."
                ariaLabel="Enable selection mode for compare"
              />
              <div className="flex items-center gap-2">
                <Label htmlFor="experiments-pin-lead" className="text-sm font-normal">
                  Pin lead columns
                </Label>
                <Switch
                  id="experiments-pin-lead"
                  checked={pinLeadColumns}
                  onCheckedChange={(v) => {
                    setPinLeadColumns(v);
                    if (projectId) {
                      saveExperimentsTablePinLead(projectId, v);
                    }
                  }}
                  aria-label="Pin grip and experiment columns when scrolling horizontally"
                />
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {showEmptyProject ? (
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
            ) : showNoSearchMatches ? (
              <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-border bg-card px-6 py-12 text-center">
                <p className="text-sm font-medium text-foreground">No experiments match this search</p>
                <p className="max-w-sm text-sm text-muted-foreground">
                  Search runs on the server across the whole project (id, name, description, tags). Try another
                  substring or clear the field to see all experiments.
                </p>
                <Button variant="outline" size="sm" type="button" onClick={() => setSearchQuery("")}>
                  Clear search
                </Button>
              </div>
            ) : (
              <ProjectDataTableFrame
                pinLeadColumns={pinLeadColumns}
                leadColumnCount={2}
                scrollContainerRef={experimentsListScrollRef}
                footer={
                  <div className="relative z-10 px-4 py-3">
                    <p className="text-xs text-muted-foreground">
                      {searchTrimmed ? (
                        <>
                          Showing {experiments.length} of {total} matching experiment{total === 1 ? "" : "s"} in this
                          project
                          {" · "}
                          drag-to-reorder is off while searching
                        </>
                      ) : (
                        <>
                          Showing {experiments.length} of {total} experiment{total === 1 ? "" : "s"} in this project
                          {experiments.length < total ? " (paginated)" : ""}
                        </>
                      )}
                    </p>
                    {(experimentsFetchingNextPage || hasNextPage) && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {experimentsFetchingNextPage
                          ? "Loading more experiments..."
                          : searchTrimmed
                            ? "Scroll down to load more matching experiments."
                            : "Scroll down to load more experiments."}
                      </p>
                    )}
                  </div>
                }
              >
                <ExperimentsTable
                  projectId={projectId}
                  experiments={experiments}
                  reorderDisabled={reorderDisabled}
                  projectMetrics={filteredMetrics}
                  metricsByExperiment={metricsByExperiment}
                  topMetrics={topMetrics}
                  parentNamesById={parentNamesById}
                  loadedExperimentNameById={loadedExperimentNameById}
                  selectedExperimentId={selectedExperimentId}
                  onExperimentClick={setSelectedExperimentId}
                  onReorder={reorderExperiments}
                  selectionMode={selectionMode}
                  getSelectionOrderNumber={getOrderNumber}
                  onSelectionToggle={toggleExperiment}
                />
                <div ref={loadMoreRef} className="h-4 shrink-0" aria-hidden="true" />
              </ProjectDataTableFrame>
            )}
          </div>
        </div>
        {selectionMode ? (
          <ExperimentCompareBar
            projectId={projectId}
            orderedIds={orderedIds}
            className="absolute bottom-6 left-6 z-20"
          />
        ) : null}
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="push"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetricsByExperiment={metricsByExperiment}
        />
      ) : null}
    </div>
  );
}
