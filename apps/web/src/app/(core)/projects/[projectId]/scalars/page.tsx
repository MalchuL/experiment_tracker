"use client";

import { useMemo, useState } from "react";
import { parseISO } from "date-fns";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { useExperiments, useProjectExperimentsPollSync } from "@/domain/experiments/hooks";
import { experimentsService } from "@/domain/experiments/services";
import type { Experiment, UpdateExperiment } from "@/domain/experiments/types";
import { ExperimentStatus } from "@/domain/experiments/types";
import { useArtifactsLiveRefresh, useProjectObjectSummaries } from "@/domain/logged-objects/hooks";
import { metricsService } from "@/domain/metrics/services";
import { useCurrentProject } from "@/domain/projects/hooks";
import {
  CreateMetricFromPointDialog,
  LoggedObjectsSection,
  ScalarExperimentsSidebar,
  ScalarPointContextMenu,
  ScalarViewSettingsSidebar,
  ScalarsDialogs,
  ScalarsMetricsGrid,
} from "@/domain/scalars/components";
import {
  useLoggedObjectsState,
  useLoggedObjectGroups,
  useMetricDomains,
  useProjectScalars,
  useScalarsDataModel,
  useScalarsLiveRefresh,
  useScalarsQueryState,
} from "@/domain/scalars/hooks";
import type {
  ArtifactViewItem,
  ScalarHoverMode,
  ScalarPointSelection,
  SyncMode,
} from "@/domain/scalars/types";
import {
  getScalarsDotThreshold,
  getScalarsMaxArtifactStepsPerObject,
  getScalarsMaxPointsPerPlot,
} from "@/domain/scalars/utils";
import type { InsertExperiment } from "@/domain/experiments/types";
import { EXPERIMENTS_LIST_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

export default function Scalars() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const searchParams = useSearchParams();
  const [fullscreenMetric, setFullscreenMetric] = useState<string | null>(null);
  const [fullscreenArtifactId, setFullscreenArtifactId] = useState<string | null>(null);
  const [syncMode, setSyncMode] = useState<SyncMode>("all");
  const [hoverMode, setHoverMode] = useState<ScalarHoverMode>("compare");
  const [soloMode, setSoloMode] = useState(false);
  const [chosenExperimentId, setChosenExperimentId] = useState<string | null>(null);
  const [experimentsSidebarOpen, setExperimentsSidebarOpen] = useState(true);
  const [settingsSidebarOpen, setSettingsSidebarOpen] = useState(true);
  const [editExperiment, setEditExperiment] = useState<Experiment | null>(null);
  const [cardHeight, setCardHeight] = useState(440);
  const [cardMinWidth, setCardMinWidth] = useState(640);
  const [hoverNameMaxLength, setHoverNameMaxLength] = useState(50);
  const [imagePreview, setImagePreview] = useState<{ src: string; title: string } | null>(null);
  const [hiddenArtifactIds, setHiddenArtifactIds] = useState<Set<string>>(new Set());
  const [pointContext, setPointContext] = useState<{
    point: ScalarPointSelection;
    position: { x: number; y: number };
  } | null>(null);
  const [metricPoint, setMetricPoint] = useState<ScalarPointSelection | null>(null);
  const [createMetricOpen, setCreateMetricOpen] = useState(false);
  const maxPointsPerPlot = useMemo(() => getScalarsMaxPointsPerPlot(), []);
  const maxArtifactStepsPerObject = useMemo(() => getScalarsMaxArtifactStepsPerObject(), []);
  const dotThreshold = useMemo(() => getScalarsDotThreshold(), []);

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
  const upsertMetric = useMutation({
    mutationFn: metricsService.upsert,
    onSuccess: (_, payload) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.GET(payload.experimentId)] });
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.BY_PROJECT(projectId)] });
      }
      setCreateMetricOpen(false);
      setMetricPoint(null);
    },
  });

  const {
    experiments = [],
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    isFetchingNextPage: experimentsFetchingNextPage,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    refetchInterval: EXPERIMENTS_LIST_POLL_INTERVAL_MS,
  });

  useProjectExperimentsPollSync(projectId, experiments);

  const sortedExperiments = useMemo(() => {
    return [...experiments].sort((a, b) => {
      return parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime();
    });
  }, [experiments]);

  const {
    scalars,
    queryKey: scalarsQueryKey,
    isLoading: scalarsLoading,
    isFetching: scalarsFetching,
    isFetchingNextPage: scalarsFetchingNextPage,
    refetch: refetchScalars,
  } = useProjectScalars({
    projectId,
    maxPoints: maxPointsPerPlot,
    returnTags: false,
  });
  const {
    artifacts: projectArtifactsAtStep,
    queryKey: artifactsQueryKey,
    isLoading: objectsLoading,
    isFetching: objectsFetching,
    isFetchingNextPage: objectsFetchingNextPage,
    refetch: refetchObjects,
  } = useProjectObjectSummaries({
    projectId,
    maxSteps: maxArtifactStepsPerObject,
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
    allChartDataByMetric,
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
  const fullscreenMetricData = fullscreenMetric ? allChartDataByMetric[fullscreenMetric] || [] : [];
  const artifactItems = useMemo<ArtifactViewItem[]>(() => {
    return Object.entries(objectGroups).flatMap(([artifactType, byName]) =>
      Object.keys(byName).map((name) => ({
        id: `${artifactType}:${name}`,
        artifactType,
        name,
        label: `${artifactType.replaceAll("_", " ")} / ${name}`,
      }))
    );
  }, [objectGroups]);

  const lastLoggedExperimentIds = useMemo(() => {
    const byId = new Map(sortedExperiments.map((e) => [e.id, e]));
    return Array.from(selectedExperimentIds).filter((id) => {
      const exp = byId.get(id);
      if (!exp) return false;
      return (
        exp.status !== ExperimentStatus.COMPLETE &&
        exp.status !== ExperimentStatus.FAILED
      );
    });
  }, [sortedExperiments, selectedExperimentIds]);

  const { refreshChangedScalars } = useScalarsLiveRefresh({
    projectId,
    experimentIds: lastLoggedExperimentIds,
    scalarsQueryKey,
    maxPoints: maxPointsPerPlot,
    enabled: !scalarsLoading,
  });

  const { refreshChangedArtifacts } = useArtifactsLiveRefresh({
    projectId,
    experimentIds: lastLoggedExperimentIds,
    artifactsQueryKey,
    maxSteps: maxArtifactStepsPerObject,
    enabled: !objectsLoading,
  });

  const handleSmoothingChange = (value: number[]) => {
    setSmoothing(value[0]);
  };

  const handleSmoothingCommit = () => {};

  const toggleSettingsSidebar = () => setSettingsSidebarOpen((prev) => !prev);
  const toggleExperimentsSidebar = () => setExperimentsSidebarOpen((prev) => !prev);

  const handleToggleSoloMode = () => {
    setSoloMode((prev) => {
      if (prev) {
        setChosenExperimentId(null);
      }
      return !prev;
    });
  };

  const handleToggleArtifact = (artifactId: string) => {
    setHiddenArtifactIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  };

  const handlePointContextMenu = (
    point: ScalarPointSelection,
    position: { x: number; y: number }
  ) => {
    setPointContext({ point, position });
  };

  const refreshButton = (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        void (async () => {
          const [incrementalScalarsRefresh, incrementalArtifactsRefresh] = await Promise.all([
            refreshChangedScalars(),
            refreshChangedArtifacts(),
          ]);
          await refetchExperiments();
          if (incrementalScalarsRefresh === "unavailable") {
            await refetchScalars();
          }
          if (incrementalArtifactsRefresh === "unavailable") {
            await refetchObjects();
          }
        })();
      }}
      disabled={scalarsFetching || experimentsFetching || objectsFetching}
      data-testid="button-refresh-scalars"
    >
      <RotateCcw
        className={`mr-2 h-4 w-4 ${
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
        onClick={toggleExperimentsSidebar}
        data-testid="button-toggle-experiments-sidebar"
      >
        {experimentsSidebarOpen ? "Hide Experiments" : "Show Experiments"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={toggleSettingsSidebar}
        data-testid="button-toggle-views-sidebar"
      >
        {settingsSidebarOpen ? "Hide Settings" : "Show Settings"}
      </Button>
    </div>
  );

  if (!projectId) {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="max-w-md text-center text-muted-foreground">
          Click on the logo in the sidebar to select a project and view its metrics.
        </p>
      </div>
    );
  }

  if (projectLoading || experimentsLoading || scalarsLoading || objectsLoading) {
    return (
      <div className="space-y-6 px-6 pt-6">
        <PageHeader title="Scalars" description="Compare scalars across experiments" actions={pageActions} />
        <ListSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 gap-0">
      {experimentsSidebarOpen ? (
        <ScalarExperimentsSidebar
          experiments={modelExperiments}
          selectedExperimentIds={selectedExperimentIds}
          soloMode={soloMode}
          chosenExperimentId={chosenExperimentId}
          setChosenExperimentId={setChosenExperimentId}
          onToggleExperiment={toggleExperiment}
          onSelectAllExperiments={selectAllExperiments}
          onClearAllExperiments={clearAllExperiments}
          onEditExperiment={setEditExperiment}
          onClose={() => setExperimentsSidebarOpen(false)}
        />
      ) : null}

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-3 pb-3 pt-3">
        <div className="mb-2">
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

        <div className="min-h-0 flex-1 overflow-auto">
          <ScalarsMetricsGrid
            visibleMetrics={visibleMetrics}
            chartDataByMetric={chartDataByMetric}
            metricDomains={metricDomains}
            cardHeight={cardHeight}
            cardMinWidth={cardMinWidth}
            smoothing={smoothing}
            dotThreshold={dotThreshold}
            hoverMode={hoverMode}
            hoverNameMaxLength={hoverNameMaxLength}
            allExperiments={modelExperiments}
            visibleExperiments={visibleExperiments}
            onResetDomain={resetDomain}
            onExpandMetric={setFullscreenMetric}
            onHideMetric={toggleMetric}
            onDomainChange={handleDomainChange}
            onHoverModeChange={setHoverMode}
            onPointContextMenu={handlePointContextMenu}
            onResizeCards={({ width, height }) => {
              setCardMinWidth(width);
              setCardHeight(height);
            }}
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
            hiddenArtifactIds={hiddenArtifactIds}
          />
        </div>
      </div>

      {settingsSidebarOpen ? (
        <ScalarViewSettingsSidebar
          projectId={projectId}
          currentQuery={currentQueryString}
          syncMode={syncMode}
          setSyncMode={setSyncMode}
          soloMode={soloMode}
          onToggleSoloMode={handleToggleSoloMode}
          cardHeight={cardHeight}
          setCardHeight={setCardHeight}
          cardMinWidth={cardMinWidth}
          setCardMinWidth={setCardMinWidth}
          hoverNameMaxLength={hoverNameMaxLength}
          setHoverNameMaxLength={setHoverNameMaxLength}
          smoothing={smoothing}
          onSmoothingChange={handleSmoothingChange}
          onSmoothingCommit={handleSmoothingCommit}
          maxPointsPerPlot={maxPointsPerPlot}
          maxArtifactStepsPerObject={maxArtifactStepsPerObject}
          dotThreshold={dotThreshold}
          allLoggedMetricNames={allLoggedMetricNames}
          hiddenMetrics={hiddenMetrics}
          artifactItems={artifactItems}
          hiddenArtifactIds={hiddenArtifactIds}
          metricDomains={metricDomains}
          onToggleMetric={toggleMetric}
          onShowAllMetrics={showAllMetrics}
          onShowOnlyMetric={showOnlyMetric}
          onExpandMetric={setFullscreenMetric}
          onResetMetricDomain={resetDomain}
          onToggleArtifact={handleToggleArtifact}
          onOpenArtifact={setFullscreenArtifactId}
          onResetAllDomains={resetAllDomains}
          onRestoreView={handleRestoreSavedView}
          onClose={() => setSettingsSidebarOpen(false)}
        />
      ) : null}

      <ScalarPointContextMenu
        point={pointContext?.point ?? null}
        position={pointContext?.position ?? null}
        onClose={() => setPointContext(null)}
        onCreateMetric={(point) => {
          setPointContext(null);
          setMetricPoint(point);
          setCreateMetricOpen(true);
        }}
      />

      <CreateMetricFromPointDialog
        point={metricPoint}
        open={createMetricOpen}
        isSaving={upsertMetric.isPending}
        onOpenChange={setCreateMetricOpen}
        onSubmit={(payload) => upsertMetric.mutate(payload)}
      />

      <ScalarsDialogs
        fullscreenMetric={fullscreenMetric}
        setFullscreenMetric={setFullscreenMetric}
        fullscreenMetricData={fullscreenMetricData}
        visibleExperiments={visibleExperiments}
        allExperiments={modelExperiments}
        metricDomains={metricDomains}
        onDomainChange={handleDomainChange}
        onResetDomain={resetDomain}
        smoothing={smoothing}
        dotThreshold={dotThreshold}
        hoverMode={hoverMode}
        hoverNameMaxLength={hoverNameMaxLength}
        onHoverModeChange={setHoverMode}
        onPointContextMenu={handlePointContextMenu}
        fullscreenArtifactId={fullscreenArtifactId}
        setFullscreenArtifactId={setFullscreenArtifactId}
        objectGroups={objectGroups}
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
