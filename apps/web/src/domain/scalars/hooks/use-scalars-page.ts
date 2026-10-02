import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ComponentProps,
} from "react";
import { useSearchParams } from "next/navigation";
import { parseISO } from "date-fns";
import {
  useExperiments,
  useProjectExperimentsPollSync,
} from "@/domain/experiments/hooks";
import { ExperimentStatus } from "@/domain/experiments/types";
import {
  useArtifactsLiveRefresh,
  useProjectObjectSummaries,
} from "@/domain/logged-objects/hooks";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useScalarsDialogState } from "./use-scalars-dialog-state";
import { useScalarsDisplayState } from "./use-scalars-display-state";
import { useLoggedObjectsState } from "./use-logged-objects-state";
import { useLoggedObjectGroups } from "./use-logged-object-groups";
import { useMetricDomains } from "./use-metric-domains";
import { useProjectScalarNames } from "./use-project-scalar-names";
import { useScalarsDataModel } from "./use-scalars-data-model";
import { useScalarsLiveRefresh } from "./use-scalars-live-refresh";
import { useScalarsQueryState } from "./use-scalars-query-state";
import type { ArtifactViewItem } from "../types";
import {
  decodeLegacyNumberSelection,
  decodeStringSelection,
  getDefaultSelectedExperimentIds,
  getScalarsDotThreshold,
  getScalarsMaxArtifactStepsPerObject,
  getScalarsMaxPointsPerPlot,
} from "../utils";
import { planManualRefreshActions } from "../utils/manual-refresh";
import { EXPERIMENTS_LIST_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import type { ScalarExperimentsSidebar } from "../components/view-settings/scalar-experiments-sidebar";
import type { ScalarViewSettingsSidebar } from "../components/view-settings/scalar-view-settings-sidebar";
import type { ScalarsContentPanel } from "../components/scalars-content-panel";
import type { ScalarsDialogs } from "../components/scalars-dialogs";
import type { ScalarPointContextMenu } from "../components/metric-create/scalar-point-context-menu";
import type { CreateMetricFromPointDialog } from "../components/metric-create/create-metric-from-point-dialog";

export function useScalarsPage() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const searchParams = useSearchParams();
  const {
    sync: { syncMode, setSyncMode },
    hover: {
      hoverMode,
      setHoverMode,
      hoverNameMaxLength,
      setHoverNameMaxLength,
    },
    solo: {
      soloMode,
      chosenExperimentId,
      handleToggleSoloMode,
      handleSoloExperimentSelect,
    },
    size: { cardHeight, setCardHeight, cardMinWidth, setCardMinWidth },
    sidebars,
  } = useScalarsDisplayState();
  const {
    fullscreen: {
      fullscreenMetric,
      setFullscreenMetric,
      fullscreenArtifactId,
      setFullscreenArtifactId,
    },
    image: { imagePreview, setImagePreview },
    experiment: { editExperiment, setEditExperiment, updateExperiment },
    metric: {
      pointContext,
      setPointContext,
      metricPoint,
      setMetricPoint,
      createMetricOpen,
      setCreateMetricOpen,
      upsertMetric,
      handlePointContextMenu,
    },
  } = useScalarsDialogState(projectId);

  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [refreshCycleStartMs, setRefreshCycleStartMs] = useState(() =>
    Date.now(),
  );
  const maxPointsPerPlot = useMemo(() => getScalarsMaxPointsPerPlot(), []);
  const maxArtifactStepsPerObject = useMemo(
    () => getScalarsMaxArtifactStepsPerObject(),
    [],
  );
  const dotThreshold = useMemo(() => getScalarsDotThreshold(), []);

  const {
    experiments = [],
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    refetch: refetchExperiments,
  } = useExperiments(projectId, {
    refetchInterval: autoRefreshEnabled
      ? EXPERIMENTS_LIST_POLL_INTERVAL_MS
      : false,
  });

  useProjectExperimentsPollSync(projectId, experiments);

  const sortedExperiments = useMemo(() => {
    return [...experiments].sort((a, b) => {
      return parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime();
    });
  }, [experiments]);

  const initialExperimentIdsFromUrl = useMemo(() => {
    const expParam = searchParams.get("exp");
    if (!expParam) return getDefaultSelectedExperimentIds(sortedExperiments);

    const validIds = new Set(
      sortedExperiments.map((experiment) => experiment.id),
    );
    const decodedIds = decodeStringSelection(expParam);
    if (decodedIds.length > 0) {
      return decodedIds.filter((id) => validIds.has(id));
    }

    return decodeLegacyNumberSelection(expParam)
      .map((index) => sortedExperiments[index]?.id)
      .filter((id): id is string => typeof id === "string");
  }, [searchParams, sortedExperiments]);

  const [requestedExperimentIds, setRequestedExperimentIds] = useState<
    string[]
  >([]);

  const {
    scalarNames: allLoggedMetricNames,
    isLoading: namesLoading,
    refetch: refetchNames,
  } = useProjectScalarNames(projectId, autoRefreshEnabled);
  const [mountedMetrics, setMountedMetrics] = useState<Set<string>>(new Set());
  const onMetricVisibilityChange = useCallback(
    (name: string, visible: boolean) => {
      setMountedMetrics((previous) => {
        if (previous.has(name) === visible) return previous;
        const next = new Set(previous);
        if (visible) next.add(name);
        else next.delete(name);
        return next;
      });
    },
    [],
  );
  const {
    artifacts: projectArtifactsAtStep,
    queryKey: artifactsQueryKey,
    isLoading: objectsLoading,
    isFetching: objectsFetching,
    refetch: refetchObjects,
  } = useProjectObjectSummaries({
    projectId,
    experimentIds: requestedExperimentIds,
    maxSteps: maxArtifactStepsPerObject,
  });

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
    scalarPage,
    setScalarPage,
    scalarPageSize,
    setScalarPageSize,
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
    metricNamesLoaded: !namesLoading,
    allArtifactIds,
  });

  useEffect(() => {
    const next = queryStateInitialized
      ? [...selectedExperimentIds].sort()
      : initialExperimentIdsFromUrl;
    setRequestedExperimentIds((previous) =>
      previous.length === next.length &&
      previous.every((id, index) => id === next[index])
        ? previous
        : next,
    );
  }, [
    initialExperimentIdsFromUrl,
    queryStateInitialized,
    selectedExperimentIds,
  ]);

  const activeMetricNames = useMemo(
    () => [
      ...new Set([
        ...mountedMetrics,
        ...(fullscreenMetric ? [fullscreenMetric] : []),
      ]),
    ],
    [mountedMetrics, fullscreenMetric],
  );
  const scalarExperimentIds = useMemo(
    () =>
      soloMode && chosenExperimentId
        ? [chosenExperimentId]
        : [...selectedExperimentIds],
    [soloMode, chosenExperimentId, selectedExperimentIds],
  );
  const {
    scalars,
    isFetching: scalarsFetching,
    statusByMetric,
    refreshChangedScalars,
    lastPollAt,
  } = useScalarsLiveRefresh({
    projectId,
    experimentIds: scalarExperimentIds,
    scalarNames: activeMetricNames,
    maxPoints: maxPointsPerPlot,
    enabled: autoRefreshEnabled,
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
    metricNames: allLoggedMetricNames,
    activeMetricNames,
  });

  const { metricDomains, handleDomainChange, resetDomain, resetAllDomains } =
    useMetricDomains(
      visibleMetrics.map((metric) => metric.name),
      syncMode,
    );

  const objectGroups = useLoggedObjectGroups(
    projectArtifactsAtStep,
    visibleExperiments,
  );
  const objectState = useLoggedObjectsState(objectGroups);
  const fullscreenMetricData = fullscreenMetric
    ? allChartDataByMetric[fullscreenMetric] || []
    : [];
  const artifactItems = useMemo<ArtifactViewItem[]>(() => {
    return Object.entries(objectGroups).flatMap(([artifactType, byName]) =>
      Object.keys(byName).map((name) => ({
        id: `${artifactType}:${name}`,
        artifactType,
        name,
        label: `${artifactType.replaceAll("_", " ")} / ${name}`,
      })),
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

  const { refreshChangedArtifacts } = useArtifactsLiveRefresh({
    projectId,
    experimentIds: lastLoggedExperimentIds,
    artifactsQueryKey,
    maxSteps: maxArtifactStepsPerObject,
    enabled: autoRefreshEnabled && !objectsLoading,
  });

  useEffect(() => {
    if (lastPollAt > 0) {
      setRefreshCycleStartMs(lastPollAt);
    }
  }, [lastPollAt]);

  const runManualRefresh = async () => {
    setRefreshCycleStartMs(Date.now());
    const [incrementalScalarsRefresh, incrementalArtifactsRefresh] =
      await Promise.all([refreshChangedScalars(), refreshChangedArtifacts()]);
    await refetchExperiments();
    const refreshPlan = planManualRefreshActions(
      incrementalScalarsRefresh,
      incrementalArtifactsRefresh,
    );
    await refetchNames();
    if (refreshPlan.refetchArtifacts) {
      await refetchObjects();
    }
  };

  const handleSmoothingChange = (value: number[]) => {
    setSmoothing(value[0]);
  };

  const handleSmoothingCommit = () => {};

  const handleToggleAutoRefresh = useCallback(() => {
    setAutoRefreshEnabled((prev) => {
      if (!prev) {
        setRefreshCycleStartMs(Date.now());
      }
      return !prev;
    });
  }, []);

  const experimentsView = {
    allExperiments: modelExperiments,
    visibleExperiments,
  };
  const display = { smoothing, dotThreshold, hoverMode, hoverNameMaxLength };
  const size = {
    cardHeight,
    cardMinWidth,
    onResizeCards: ({ width, height }: { width: number; height: number }) => {
      setCardMinWidth(width);
      setCardHeight(height);
    },
  };
  const zoom = {
    metricDomains,
    onResetDomain: resetDomain,
    onDomainChange: handleDomainChange,
  };
  const interactions = {
    onHoverModeChange: setHoverMode,
    onPointContextMenu: handlePointContextMenu,
  };
  const steps = {
    objectStepSelection: objectState.objectStepSelection,
    updateObjectStep: objectState.updateObjectStep,
    debouncedObjectStepSelection: objectState.debouncedObjectStepSelection,
  };
  const overrides = {
    experimentStepOverrideEnabled: objectState.experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled:
      objectState.setExperimentStepOverrideEnabled,
    enableExperimentStepOverride: objectState.enableExperimentStepOverride,
    experimentStepOverrides: objectState.experimentStepOverrides,
    updateExperimentStepOverride: objectState.updateExperimentStepOverride,
    debouncedExperimentStepOverrides:
      objectState.debouncedExperimentStepOverrides,
  };
  const view = projectId
    ? {
        experiments: {
          onClose: () => sidebars.experiments.setOpen(false),
          list: {
            items: {
              experiments: modelExperiments,
              onEditExperiment: setEditExperiment,
            },
            selection: {
              selectedExperimentIds,
              onToggleExperiment: toggleExperiment,
              onSelectAllExperiments: selectAllExperiments,
              onClearAllExperiments: clearAllExperiments,
            },
            solo: {
              soloMode,
              chosenExperimentId,
              onSoloExperimentSelect: handleSoloExperimentSelect,
            },
          },
        } satisfies ComponentProps<typeof ScalarExperimentsSidebar>,
        content: {
          scalars: {
            experiments: experimentsView,
            display,
            size,
            zoom,
            actions: {
              ...interactions,
              onExpandMetric: setFullscreenMetric,
              onHideMetric: toggleMetric,
            },
            loading: { onMetricVisibilityChange, statusByMetric },
            metrics: { visibleMetrics, chartDataByMetric },
          },
          pagination: {
            scalarPage,
            scalarPageSize,
            onPageChange: setScalarPage,
            onPageSizeChange: setScalarPageSize,
          },
          artifacts: {
            data: {
              projectId,
              objectGroups,
              hiddenArtifactIds,
              onImagePreview: setImagePreview,
            },
            steps,
            overrides,
          },
        } satisfies ComponentProps<typeof ScalarsContentPanel>,
        settings: {
          onClose: () => sidebars.settings.setOpen(false),
          display: {
            sync: { syncMode, setSyncMode },
            solo: { soloMode, onToggleSoloMode: handleToggleSoloMode },
            size: { cardHeight, setCardHeight, cardMinWidth, setCardMinWidth },
            hover: { hoverNameMaxLength, setHoverNameMaxLength },
            smoothing: {
              smoothing,
              onSmoothingChange: handleSmoothingChange,
              onSmoothingCommit: handleSmoothingCommit,
            },
            limits: {
              maxPointsPerPlot,
              maxArtifactStepsPerObject,
              dotThreshold,
            },
          },
          visibility: {
            scalars: {
              allLoggedMetricNames,
              hiddenMetrics,
              metricDomains,
              onToggleMetric: toggleMetric,
              onShowAllMetrics: showAllMetrics,
              onShowOnlyMetric: showOnlyMetric,
              onExpandMetric: setFullscreenMetric,
              onResetMetricDomain: resetDomain,
            },
            artifacts: {
              artifactItems,
              hiddenArtifactIds,
              onToggleArtifact: toggleArtifact,
              onOpenArtifact: setFullscreenArtifactId,
            },
          },
          views: {
            projectId,
            currentQuery: currentQueryString,
            onRestoreView: handleRestoreSavedView,
          },
          zoom: { onResetAllDomains: resetAllDomains },
        } satisfies ComponentProps<typeof ScalarViewSettingsSidebar>,
        dialogs: {
          scalar: {
            selection: {
              fullscreenMetric,
              setFullscreenMetric,
              fullscreenMetricData,
            },
            experiments: experimentsView,
            zoom,
            display,
            interactions,
          },
          artifact: {
            selection: { fullscreenArtifactId, setFullscreenArtifactId },
            data: { projectId, objectGroups },
            size,
            steps,
            overrides,
          },
          image: { imagePreview, setImagePreview },
          experiment: {
            editExperiment,
            setEditExperiment,
            isSavingExperiment: updateExperiment.isPending,
            onSaveExperiment: (payload, onSuccess) =>
              updateExperiment.mutate(payload, { onSuccess }),
          },
        } satisfies ComponentProps<typeof ScalarsDialogs>,
        pointMenu: {
          point: pointContext?.point ?? null,
          position: pointContext?.position ?? null,
          onClose: () => setPointContext(null),
          onCreateMetric: (point) => {
            setPointContext(null);
            setMetricPoint(point);
            setCreateMetricOpen(true);
          },
        } satisfies ComponentProps<typeof ScalarPointContextMenu>,
        metricForm: {
          point: metricPoint,
          open: createMetricOpen,
          isSaving: upsertMetric.isPending,
          onOpenChange: setCreateMetricOpen,
          onSubmit: (payload) => upsertMetric.mutate(payload),
        } satisfies ComponentProps<typeof CreateMetricFromPointDialog>,
      }
    : null;
  return {
    project,
    loading: projectLoading || experimentsLoading || namesLoading,
    view,
    actions: {
      refresh: {
        isFetching: scalarsFetching || experimentsFetching || objectsFetching,
        onRefresh: runManualRefresh,
        autoRefreshEnabled,
        cycleStartMs: refreshCycleStartMs,
        onToggleAutoRefresh: handleToggleAutoRefresh,
      },
      sidebars,
    },
  };
}
