"use client";

import { useMemo, useRef } from "react";
import { Loader2 } from "lucide-react";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { ProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { Button } from "@/components/ui/button";
import { useAggregatedMetrics } from "@/domain/experiments/hooks";
import { getDisplayedTrackedMetrics } from "@/lib/metrics/format-metric-label";
import { REFRESH_EXPERIMENTS_LIST_INTERVAL } from "@/lib/constants/rates";
import {
  ProjectMetricsPageIntro,
  ProjectMetricsPageUsageHint,
} from "./components/project-metrics-page-intro";
import { ProjectMetricsTableToolbar } from "./components/project-metrics-table-toolbar";
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
    pinLeadColumns,
    setPinLeadColumns,
  } = useProjectMetricsPageState();

  const metricsScrollRef = useRef<HTMLDivElement>(null);

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

  const canShowTable = !dataLoading && label !== null && latest != null;
  const showDownload =
    canShowTable && !editMode && table.getRowModel().rows.length > 0;

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
    <div className="flex h-full min-h-0 w-full min-w-0 gap-0">
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
            pinLeadColumns={pinLeadColumns}
            onPinLeadColumnsChange={setPinLeadColumns}
          />

          <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden">
            <div className="shrink-0">
              <ProjectMetricsPageIntro projectName={project?.name} />
            </div>
            <ProjectDataTableFrame
              pinLeadColumns={pinLeadColumns}
              leadColumnCount={1}
              scrollContainerRef={metricsScrollRef}
              className="min-h-0"
              toolbar={
                <ProjectMetricsTableToolbar
                  table={table}
                  exportFileBase={exportFileBase}
                  showDownload={showDownload}
                />
              }
              footer={
                hasNextPage || latest ? (
                  <div className="space-y-2 px-4 py-3">
                    {hasNextPage ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void fetchNextPage()}
                        disabled={isFetchingNextPage}
                        type="button"
                      >
                        {isFetchingNextPage ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Loading…
                          </>
                        ) : (
                          "Load more experiments"
                        )}
                      </Button>
                    ) : null}
                    {latest ? (
                      <p className="text-xs text-muted-foreground">
                        Showing {tableData.length} experiment{tableData.length === 1 ? "" : "s"} in the table
                        {nameFilter ? " (name filter on loaded data)" : ""}
                        {" · Metric columns come from the selected label snapshot."}
                        {editMode ? ` — report when edit is off: ${rowsInReport.length} row(s)` : null}
                        {hiddenRowIds.size > 0 ? ` — ${hiddenRowIds.size} row(s) hidden in report` : ""}
                        {hiddenColumnIds.size > 0 ? ` — ${hiddenColumnIds.size} column(s) hidden in report` : ""} ·{" "}
                        {latest.total} in project for this label
                      </p>
                    ) : null}
                  </div>
                ) : undefined
              }
            >
              <ProjectMetricsTableSection
                dataLoading={dataLoading}
                isError={isError}
                canShowTable={canShowTable}
                table={table}
                editMode={editMode}
                rowsInReport={rowsInReport}
                filteredRows={filteredRows}
                selectedExperimentId={selectedExperimentId}
              />
            </ProjectDataTableFrame>
            <div className="shrink-0">
              <ProjectMetricsPageUsageHint />
            </div>
          </div>
        </div>
      </div>

      {selectedExperimentId ? (
        <ExperimentSidebar
          variant="push"
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={projectMetricsForSidebar}
          aggregatedMetricsByExperiment={aggregatedMetricsByExperiment}
        />
      ) : null}
    </div>
  );
}
