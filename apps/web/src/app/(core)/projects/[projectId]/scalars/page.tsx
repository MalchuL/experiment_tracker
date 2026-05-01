"use client";

import { parseISO } from "date-fns";
import { InfiniteData, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { useExperiments } from "@/domain/experiments/hooks";
import { experimentsService } from "@/domain/experiments/services";
import type { Experiment, UpdateExperiment } from "@/domain/experiments/types";
import { useProjectObjects } from "@/domain/logged-objects/hooks";
import { useCurrentProject } from "@/domain/projects/hooks";
import {
  LoggedObjectsSection,
  ScalarViewsSidebar,
  ScalarsControlsPanel,
  ScalarsDialogs,
  ScalarsMetricsGrid,
} from "@/domain/scalars/components";
import {
  useLoggedObjectsState,
  useLoggedObjectGroups,
  useMetricDomains,
  useProjectScalars,
  useScalarsDataModel,
  useScalarsQueryState,
} from "@/domain/scalars/hooks";
import type { SyncMode } from "@/domain/scalars/types";
import type { InsertExperiment } from "@/shared/schema";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";

export default function Scalars() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const searchParams = useSearchParams();
  const [fullscreenMetric, setFullscreenMetric] = useState<string | null>(null);
  const [syncMode, setSyncMode] = useState<SyncMode>("all");
  const [soloMode, setSoloMode] = useState(false);
  const [chosenExperimentId, setChosenExperimentId] = useState<string | null>(null);
  const [viewsSidebarOpen, setViewsSidebarOpen] = useState(true);
  const [editExperiment, setEditExperiment] = useState<Experiment | null>(null);
  const [cardHeight, setCardHeight] = useState(220);
  const [cardMinWidth, setCardMinWidth] = useState(320);
  const [imagePreview, setImagePreview] = useState<{ src: string; title: string } | null>(null);

  const queryClient = useQueryClient();
  const updateExperiment = useMutation({
    mutationFn: (payload: { id: string; data: UpdateExperiment }) =>
      experimentsService.update(payload.id, payload.data as unknown as InsertExperiment),
    onSuccess: () => {
      if (!projectId) return;
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
      });
    },
  });

  const {
    experiments = [],
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    refetch: refetchExperiments,
  } = useExperiments(projectId);

  const sortedExperiments = useMemo(() => {
    return [...experiments].sort((a, b) => {
      return parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime();
    });
  }, [experiments]);

  const {
    scalars,
    isLoading: scalarsLoading,
    isFetching: scalarsFetching,
    isFetchingNextPage: scalarsFetchingNextPage,
    refetch: refetchScalars,
  } = useProjectScalars({
    projectId,
    returnTags: false,
  });
  const {
    artifacts: projectArtifactsAtStep,
    isLoading: objectsLoading,
    isFetching: objectsFetching,
    isFetchingNextPage: objectsFetchingNextPage,
    refetch: refetchObjects,
  } = useProjectObjects({
    projectId,
  });

  const allLoggedMetricNames = useMemo(() => {
    const metricSet = new Set<string>();
    scalars.forEach((experimentScalars) => {
      Object.keys(experimentScalars.scalars || {}).forEach((name) => metricSet.add(name));
    });
    return Array.from(metricSet).sort();
  }, [scalars]);

  const {
    smoothing,
    setSmoothing,
    selectedExperimentIds,
    hiddenMetrics,
    currentQueryString,
    setSelectedExperimentIds,
    toggleExperiment,
    selectAllExperiments,
    clearAllExperiments,
    toggleMetric,
    showAllMetrics,
    showOnlyMetric,
    handleRestoreSavedView,
  } = useScalarsQueryState({
    projectId,
    searchParams,
    experiments: sortedExperiments,
    allLoggedMetricNames,
  });

  const {
    sortedExperiments: modelExperiments,
    visibleMetrics,
    visibleExperiments,
    chartDataByMetric,
  } = useScalarsDataModel({
    experiments,
    scalars,
    selectedExperimentIds,
    hiddenMetrics,
    smoothing,
    soloMode,
    chosenExperimentId,
  });

  const { metricDomains, handleDomainChange, resetDomain, resetAllDomains } = useMetricDomains(
    visibleMetrics.map((metric) => metric.name),
    syncMode
  );

  const objectState = useLoggedObjectsState();
  const objectGroups = useLoggedObjectGroups(projectArtifactsAtStep, visibleExperiments);
  const fullscreenMetricData = fullscreenMetric ? chartDataByMetric[fullscreenMetric] || [] : [];

  const handleSmoothingChange = (value: number[]) => {
    setSmoothing(value[0]);
  };

  const handleSmoothingCommit = () => {};

  const refreshButton = (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        void (async () => {
          const hadAllSelected = selectedExperimentIds.size === modelExperiments.length;
          await refetchExperiments();
          await refetchScalars();
          await refetchObjects();
          if (hadAllSelected && projectId) {
            const refreshedExperimentsData = queryClient.getQueryData<
              InfiniteData<{ data: Experiment[] }>
            >([
              QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId),
              { limit: DEFAULT_PAGE_SIZE, mode: "auto" },
            ]);
            const refreshedExperiments =
              refreshedExperimentsData?.pages.flatMap((page) => page.data) ?? [];
            const allIds = new Set(refreshedExperiments.map((experiment) => experiment.id));
            setSelectedExperimentIds(allIds);
          }
        })();
      }}
      disabled={scalarsFetching || experimentsFetching || objectsFetching}
      data-testid="button-refresh-scalars"
    >
      <RotateCcw
        className={`w-4 h-4 mr-2 ${
          scalarsFetching || experimentsFetching || objectsFetching ? "animate-spin" : ""
        }`}
      />
      {scalarsFetching || experimentsFetching || objectsFetching ? "Refreshing..." : "Refresh"}
    </Button>
  );

  const pageActions = (
    <div className="flex items-center gap-2">
      {refreshButton}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setViewsSidebarOpen((prev) => !prev)}
        data-testid="button-toggle-views-sidebar"
      >
        {viewsSidebarOpen ? "Hide Views" : "Show Views"}
      </Button>
    </div>
  );

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its metrics.
        </p>
      </div>
    );
  }

  if (projectLoading || experimentsLoading || scalarsLoading || objectsLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Scalars" description="Compare scalars across experiments" actions={pageActions} />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className={`flex h-[calc(100vh-5rem)] gap-4 ${viewsSidebarOpen ? "pr-80" : ""}`}>
      <ScalarsControlsPanel
        syncMode={syncMode}
        setSyncMode={setSyncMode}
        soloMode={soloMode}
        onToggleSoloMode={() =>
          setSoloMode((prev) => {
            if (prev) {
              setChosenExperimentId(null);
            }
            return !prev;
          })
        }
        cardHeight={cardHeight}
        setCardHeight={setCardHeight}
        cardMinWidth={cardMinWidth}
        setCardMinWidth={setCardMinWidth}
        smoothing={smoothing}
        onSmoothingChange={handleSmoothingChange}
        onSmoothingCommit={handleSmoothingCommit}
        experiments={modelExperiments}
        selectedExperimentIds={selectedExperimentIds}
        chosenExperimentId={chosenExperimentId}
        setChosenExperimentId={setChosenExperimentId}
        onToggleExperiment={toggleExperiment}
        onSelectAllExperiments={selectAllExperiments}
        onClearAllExperiments={clearAllExperiments}
        allLoggedMetricNames={allLoggedMetricNames}
        hiddenMetrics={hiddenMetrics}
        onToggleMetric={toggleMetric}
        onShowAllMetrics={showAllMetrics}
        onShowOnlyMetric={showOnlyMetric}
        onExpandMetric={setFullscreenMetric}
        metricDomains={metricDomains}
        onResetMetricDomain={resetDomain}
        onEditExperiment={setEditExperiment}
        onResetAllDomains={resetAllDomains}
      />

      <div className="flex-1 overflow-auto">
        <div className="mb-4">
          <PageHeader
            title="Scalars"
            description={`Scalars visualization for "${project?.name}" - ${visibleExperiments.length} experiments visible`}
            actions={pageActions}
          />
          {(experimentsFetchingNextPage ||
            scalarsFetchingNextPage ||
            objectsFetchingNextPage) && (
            <p className="mt-2 text-sm text-muted-foreground">
              Loading additional experiments, scalars, and logged objects...
            </p>
          )}
        </div>

        <ScalarsMetricsGrid
          visibleMetrics={visibleMetrics}
          chartDataByMetric={chartDataByMetric}
          metricDomains={metricDomains}
          cardHeight={cardHeight}
          cardMinWidth={cardMinWidth}
          allExperiments={modelExperiments}
          visibleExperiments={visibleExperiments}
          onResetDomain={resetDomain}
          onExpandMetric={setFullscreenMetric}
          onHideMetric={toggleMetric}
          onDomainChange={handleDomainChange}
        />

        <LoggedObjectsSection
          objectGroups={objectGroups}
          visibleExperiments={visibleExperiments}
          cardMinWidth={cardMinWidth}
          cardHeight={cardHeight}
          objectStepSelection={objectState.objectStepSelection}
          setObjectStepSelection={objectState.setObjectStepSelection}
          debouncedObjectStepSelection={objectState.debouncedObjectStepSelection}
          experimentStepOverrideEnabled={objectState.experimentStepOverrideEnabled}
          setExperimentStepOverrideEnabled={objectState.setExperimentStepOverrideEnabled}
          experimentStepOverrides={objectState.experimentStepOverrides}
          setExperimentStepOverrides={objectState.setExperimentStepOverrides}
          debouncedExperimentStepOverrides={objectState.debouncedExperimentStepOverrides}
          onImagePreview={setImagePreview}
        />
      </div>

      {viewsSidebarOpen && (
        <ScalarViewsSidebar
          projectId={projectId}
          currentQuery={currentQueryString}
          onRestoreView={handleRestoreSavedView}
          onClose={() => setViewsSidebarOpen(false)}
        />
      )}

      <ScalarsDialogs
        fullscreenMetric={fullscreenMetric}
        setFullscreenMetric={setFullscreenMetric}
        fullscreenMetricData={fullscreenMetricData}
        visibleExperiments={visibleExperiments}
        allExperiments={modelExperiments}
        metricDomains={metricDomains}
        onDomainChange={handleDomainChange}
        onResetDomain={resetDomain}
        imagePreview={imagePreview}
        setImagePreview={setImagePreview}
        editExperiment={editExperiment}
        setEditExperiment={setEditExperiment}
        isSavingExperiment={updateExperiment.isPending}
        onSaveExperiment={(payload, onSuccess) => {
          updateExperiment.mutate(payload, { onSuccess });
        }}
      />
    </div>
  );
}

