"use client";

import { useMemo } from "react";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { useAggregatedMetrics } from "@/domain/experiments/hooks";
import { getDisplayedTrackedMetrics } from "@/lib/metrics/format-metric-label";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import {
  ProjectMetricsPageIntro,
  ProjectMetricsPageUsageHint,
} from "./components/project-metrics-page-intro";
import {
  ProjectMetricsLabelListError,
  ProjectMetricsLoadingProject,
  ProjectMetricsNoLoggedMetrics,
  ProjectMetricsNoProject,
} from "./components/project-metrics-page-states";
import { useProjectMetricsPageState } from "./hooks/use-project-metrics-page-state";
import { ProjectMetricsControlPanel } from "./project-metrics-control-panel";
import { ProjectMetricsTableSection } from "./project-metrics-table-section";

/**
 * Project-scoped metrics pivot: one `label` at a time, experiments × metric names. Controls sit in a
 * left rail (like Scalars); the table scrolls in the main column. Table width/order persist; row/column
 * /tint/min-max session state is lost on full reload.
 */
export function ProjectMetricsPage() {
  const {
    project,
    projectId,
    projectLoading,
    labelsLoading,
    labelData,
    hasAnyLabel,
    label,
    setLabel,
    includeAll,
    setIncludeAll,
    nameFilter,
    setNameFilter,
    editMode,
    setEditMode,
    isError,
    dataLoading,
    latest,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    filteredRows,
    rowsInReport,
    tableData,
    table,
    hiddenRowIds,
    hiddenColumnIds,
    selectedExperimentId,
    setSelectedExperimentId,
  } = useProjectMetricsPageState();

  const { aggregatedMetricsByExperiment } = useAggregatedMetrics(projectId, {
    refetchInterval: REFRESH_EXPERIMENTS_LIST_INTERVAL,
  });

  const projectMetricsForSidebar = useMemo(() => {
    if (!project?.metrics) return [];
    return getDisplayedTrackedMetrics(project.metrics.trackedMetrics, project.metrics.displayMetrics);
  }, [project]);

  const exportFileBase = useMemo(() => {
    const safe =
      label === null
        ? "no-label"
        : label === ""
          ? "unlabeled"
          : label.replace(/[^\w.\-]+/g, "-").replace(/^-|-$/g, "") || "label";
    return `project-metrics-${projectId?.slice(0, 8) ?? "project"}-${safe}`;
  }, [label, projectId]);

  if (!projectId) {
    return <ProjectMetricsNoProject />;
  }
  if (projectLoading || labelsLoading) {
    return <ProjectMetricsLoadingProject />;
  }
  if (!labelData) {
    return <ProjectMetricsLabelListError />;
  }
  if (!hasAnyLabel) {
    return <ProjectMetricsNoLoggedMetrics projectName={project?.name} />;
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full min-w-0 gap-0">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-6 pt-6 pb-6">
        <div className="box-border flex min-h-0 flex-1 flex-col gap-4 lg:flex-row lg:items-stretch">
          <ProjectMetricsControlPanel
            labelData={labelData}
            label={label}
            onLabelChange={setLabel}
            includeAll={includeAll}
            onIncludeAllChange={setIncludeAll}
            nameFilter={nameFilter}
            onNameFilterChange={setNameFilter}
            editMode={editMode}
            onEditModeChange={setEditMode}
          />

          <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden">
            <ProjectMetricsPageIntro projectName={project?.name} />
            <div className="min-h-0 flex-1 overflow-auto">
              <ProjectMetricsTableSection
                dataLoading={dataLoading}
                isError={isError}
                canShowTable={!dataLoading && label !== null && latest != null}
                table={table}
                editMode={editMode}
                nameFilter={nameFilter}
                rowsInReport={rowsInReport}
                filteredRows={filteredRows}
                hasNextPage={hasNextPage}
                isFetchingNextPage={isFetchingNextPage}
                onLoadMore={() => void fetchNextPage()}
                latest={latest}
                tableDataLength={tableData.length}
                hiddenRowIds={hiddenRowIds}
                hiddenColumnIds={hiddenColumnIds}
                selectedExperimentId={selectedExperimentId}
                exportFileBase={exportFileBase}
              />
            </div>
            <ProjectMetricsPageUsageHint />
          </div>
        </div>
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="push"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={projectMetricsForSidebar}
          aggregatedMetrics={aggregatedMetricsByExperiment[selectedExperimentId] ?? undefined}
        />
      ) : null}
    </div>
  );
}
