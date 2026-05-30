"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { parseISO } from "date-fns";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { InfiniteData } from "@tanstack/react-query";
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
import { loggedObjectsService } from "@/domain/logged-objects/services";
import type { ArtifactsInfoSummaryResult } from "@/domain/logged-objects/types";
import { mergeArtifactsInfoPage } from "@/domain/logged-objects/utils";
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
  ScalarsPointsResult,
  SyncMode,
} from "@/domain/scalars/types";
import { scalarsService } from "@/domain/scalars/services";
import {
  decodeLegacyNumberSelection,
  decodeStringSelection,
  getScalarsDotThreshold,
  getScalarsMaxArtifactStepsPerObject,
  getScalarsMaxPointsPerPlot,
  mergeScalarsPage,
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
  const [pointContext, setPointContext] = useState<{
    point: ScalarPointSelection;
    position: { x: number; y: number };
  } | null>(null);
  const [metricPoint, setMetricPoint] = useState<ScalarPointSelection | null>(null);
  const [createMetricOpen, setCreateMetricOpen] = useState(false);
  const incrementalInFlightIds = useRef<Set<string>>(new Set());
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

  const initialExperimentIdsFromUrl = useMemo(() => {
    const expParam = searchParams.get("exp");
    if (!expParam) return sortedExperiments.map((experiment) => experiment.id);

    const validIds = new Set(sortedExperiments.map((experiment) => experiment.id));
    const decodedIds = decodeStringSelection(expParam);
    if (decodedIds.length > 0) {
      return decodedIds.filter((id) => validIds.has(id));
    }

    return decodeLegacyNumberSelection(expParam)
      .map((index) => sortedExperiments[index]?.id)
      .filter((id): id is string => typeof id === "string");
  }, [searchParams, sortedExperiments]);

  const [requestedExperimentIds, setRequestedExperimentIds] = useState<string[]>([]);

  const {
    scalars,
    queryKey: scalarsQueryKey,
    isLoading: scalarsLoading,
    isFetching: scalarsFetching,
    isFetchingNextPage: scalarsFetchingNextPage,
    refetch: refetchScalars,
  } = useProjectScalars({
    projectId,
    experimentIds: requestedExperimentIds,
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
    experimentIds: requestedExperimentIds,
    maxSteps: maxArtifactStepsPerObject,
  });

  const allLoggedMetricNames = useMemo(() => {
    const metricSet = new Set<string>();
    scalars.forEach((experimentScalars) => {
      Object.keys(experimentScalars.scalars || {}).forEach((name) => metricSet.add(name));
    });
    return Array.from(metricSet).sort();
  }, [scalars]);

  const allArtifactIds = useMemo(() => {
    const ids = new Set<string>();
    projectArtifactsAtStep.forEach((experimentArtifacts) => {
      experimentArtifacts.artifacts_info.forEach((artifact) => {
        ids.add(`${artifact.artifact_type}:${artifact.name}`);
      });
    });
    return Array.from(ids).sort();
  }, [projectArtifactsAtStep]);

  const {
    smoothing,
    setSmoothing,
    initialized: queryStateInitialized,
    selectedExperimentIds,
    hiddenMetrics,
    hiddenArtifactIds,
    currentQueryString,
    toggleExperiment,
    selectAllExperiments,
    clearAllExperiments,
    toggleMetric,
    toggleArtifact,
    showAllMetrics,
    showOnlyMetric,
    handleRestoreSavedView,
  } = useScalarsQueryState({
    projectId,
    searchParams,
    experiments: sortedExperiments,
    allLoggedMetricNames,
    allArtifactIds,
  });

  useEffect(() => {
    if (queryStateInitialized) return;
    setRequestedExperimentIds(initialExperimentIdsFromUrl);
    incrementalInFlightIds.current.clear();
  }, [initialExperimentIdsFromUrl, queryStateInitialized]);

  useEffect(() => {
    if (!queryStateInitialized || !projectId || !scalarsQueryKey.length || !artifactsQueryKey.length) return;

    const fetchedIds = new Set([
      ...requestedExperimentIds,
      ...scalars.map((item) => item.experiment_id),
    ]);
    const missingIds = Array.from(selectedExperimentIds).filter(
      (id) => !fetchedIds.has(id) && !incrementalInFlightIds.current.has(id)
    );
    if (missingIds.length === 0) return;

    missingIds.forEach((id) => incrementalInFlightIds.current.add(id));
    let cancelled = false;

    void Promise.all([
      scalarsService.getByProject(projectId, {
        experimentIds: missingIds,
        limit: Math.max(missingIds.length, 1),
        maxPoints: maxPointsPerPlot,
        returnTags: false,
      }),
      loggedObjectsService.getSummaryByProject(projectId, {
        experimentIds: missingIds,
        limit: Math.max(missingIds.length, 1),
        maxSteps: maxArtifactStepsPerObject,
      }),
    ])
      .then(([scalarsResult, artifactsResult]) => {
        if (cancelled) return;
        queryClient.setQueryData<InfiniteData<ScalarsPointsResult>>(scalarsQueryKey, (current) => {
          if (!current) return current;
          return {
            ...current,
            pages: current.pages.map((page, index) =>
              mergeScalarsPage(page, scalarsResult.data, {
                appendMissing: index === 0,
                maxPoints: maxPointsPerPlot,
              })
            ),
          };
        });
        queryClient.setQueryData<InfiniteData<ArtifactsInfoSummaryResult>>(artifactsQueryKey, (current) => {
          if (!current) return current;
          return {
            ...current,
            pages: current.pages.map((page, index) =>
              mergeArtifactsInfoPage(page, artifactsResult.data, { appendMissing: index === 0 })
            ),
          };
        });
      })
      .catch((error: unknown) => {
        console.error("failed_to_fetch_selected_experiments", error);
      })
      .finally(() => {
        missingIds.forEach((id) => incrementalInFlightIds.current.delete(id));
      });

    return () => {
      cancelled = true;
    };
  }, [
    artifactsQueryKey,
    maxArtifactStepsPerObject,
    maxPointsPerPlot,
    projectId,
    queryClient,
    queryStateInitialized,
    requestedExperimentIds,
    scalars,
    scalarsQueryKey,
    selectedExperimentIds,
  ]);

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

  const hasInitialScalars = scalars.length > 0;
  const hasInitialArtifacts = projectArtifactsAtStep.length > 0;
  if (
    projectLoading ||
    experimentsLoading ||
    (scalarsLoading && !hasInitialScalars) ||
    (objectsLoading && !hasInitialArtifacts)
  ) {
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
            projectId={projectId}
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
          onToggleArtifact={toggleArtifact}
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
        projectId={projectId}
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
