"use client";

import { useMemo, useState } from "react";
import type { ComponentProps, Dispatch, SetStateAction } from "react";
import { EmptyState } from "@/components/shared/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Experiment } from "@/domain/experiments/types";
import { CollapsiblePrefixGroup } from "@/domain/scalars/components/collapsible-prefix-group";
import { LoggedObjectsSection } from "@/domain/scalars/components/logged-objects-section";
import { ScalarsMetricsGrid } from "@/domain/scalars/components/scalars-metrics-grid";
import type {
  ChartDomain,
  LoggedObjectGroups,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
} from "@/domain/scalars/types";
import {
  buildScalarsContentTabs,
  partitionNamesByPrefixForTab,
  SCALARS_CONTENT_TAB_ID,
  visibleArtifactNamesForType,
} from "@/domain/scalars/utils/scalars-content-layout";
import { BarChart3 } from "lucide-react";

interface MetricItem {
  name: string;
}

export interface ScalarsContentPanelProps {
  visibleMetrics: MetricItem[];
  chartDataByMetric: Record<string, ScalarChartPoint[]>;
  metricDomains: Record<string, ChartDomain>;
  cardHeight: number;
  cardMinWidth: number;
  smoothing?: number;
  dotThreshold?: number;
  hoverMode?: ScalarHoverMode;
  hoverNameMaxLength?: number;
  allExperiments: Experiment[];
  visibleExperiments: Experiment[];
  onResetDomain: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onHideMetric: (metricName: string) => void;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  onResizeCards?: (size: { width: number; height: number }) => void;
  onHoverModeChange?: (mode: ScalarHoverMode) => void;
  onPointContextMenu?: (point: ScalarPointSelection, position: { x: number; y: number }) => void;
  projectId: string;
  objectGroups: LoggedObjectGroups;
  hiddenArtifactIds: Set<string>;
  objectStepSelection: Record<string, number>;
  updateObjectStep: (selectionKey: string, step: number, followLatest: boolean) => void;
  debouncedObjectStepSelection: Record<string, number>;
  experimentStepOverrideEnabled: Record<string, boolean>;
  setExperimentStepOverrideEnabled: Dispatch<SetStateAction<Record<string, boolean>>>;
  enableExperimentStepOverride: (overrideKey: string, step: number, followLatest?: boolean) => void;
  experimentStepOverrides: Record<string, number>;
  updateExperimentStepOverride: (overrideKey: string, step: number, followLatest: boolean) => void;
  debouncedExperimentStepOverrides: Record<string, number>;
  onImagePreview: (payload: { src: string; title: string }) => void;
}

function MetricsPrefixSection({
  metricNames,
  gridProps,
}: {
  metricNames: string[];
  gridProps: Omit<ComponentProps<typeof ScalarsMetricsGrid>, "visibleMetrics">;
}) {
  const visibleMetrics = metricNames.map((name) => ({ name }));
  return <ScalarsMetricsGrid {...gridProps} visibleMetrics={visibleMetrics} />;
}

export function ScalarsContentPanel({
  visibleMetrics,
  chartDataByMetric,
  metricDomains,
  cardHeight,
  cardMinWidth,
  smoothing = 0,
  dotThreshold = 10,
  hoverMode = "compare",
  hoverNameMaxLength = 50,
  allExperiments,
  visibleExperiments,
  onResetDomain,
  onExpandMetric,
  onHideMetric,
  onDomainChange,
  onResizeCards = () => {},
  onHoverModeChange = () => {},
  onPointContextMenu = () => {},
  projectId,
  objectGroups,
  hiddenArtifactIds,
  objectStepSelection,
  updateObjectStep,
  debouncedObjectStepSelection,
  experimentStepOverrideEnabled,
  setExperimentStepOverrideEnabled,
  enableExperimentStepOverride,
  experimentStepOverrides,
  updateExperimentStepOverride,
  debouncedExperimentStepOverrides,
  onImagePreview,
}: ScalarsContentPanelProps) {
  const tabs = useMemo(
    () =>
      buildScalarsContentTabs({
        visibleMetricNames: visibleMetrics.map((metric) => metric.name),
        objectGroups,
        hiddenArtifactIds,
      }),
    [visibleMetrics, objectGroups, hiddenArtifactIds]
  );

  const [activeTab, setActiveTab] = useState(() => tabs[0]?.id ?? SCALARS_CONTENT_TAB_ID);

  const resolvedActiveTab = tabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : (tabs[0]?.id ?? SCALARS_CONTENT_TAB_ID);

  const scalarPartition = useMemo(
    () => partitionNamesByPrefixForTab(visibleMetrics.map((metric) => metric.name)),
    [visibleMetrics]
  );

  const metricsGridProps = {
    chartDataByMetric,
    metricDomains,
    cardHeight,
    cardMinWidth,
    smoothing,
    dotThreshold,
    hoverMode,
    hoverNameMaxLength,
    allExperiments,
    visibleExperiments,
    onResetDomain,
    onExpandMetric,
    onHideMetric,
    onDomainChange,
    onResizeCards,
    onHoverModeChange,
    onPointContextMenu,
  };

  const loggedObjectsBaseProps = {
    projectId,
    objectGroups,
    visibleExperiments,
    cardMinWidth,
    cardHeight,
    objectStepSelection,
    updateObjectStep,
    debouncedObjectStepSelection,
    experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled,
    enableExperimentStepOverride,
    experimentStepOverrides,
    updateExperimentStepOverride,
    debouncedExperimentStepOverrides,
    onImagePreview,
    hiddenArtifactIds,
    showSectionHeader: false,
  };

  if (tabs.length === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No scalars or logged objects"
        description="Select experiments with logged metrics or artifacts to view them here."
      />
    );
  }

  return (
    <Tabs value={resolvedActiveTab} onValueChange={setActiveTab} className="space-y-3">
      <TabsList className="h-auto flex-wrap justify-start">
        {tabs.map((tab) => (
          <TabsTrigger key={tab.id} value={tab.id}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {tabs.map((tab) => (
        <TabsContent key={tab.id} value={tab.id} forceMount className="space-y-4 data-[state=inactive]:hidden">
          {tab.id === SCALARS_CONTENT_TAB_ID ? (
            <>
              {scalarPartition.ungrouped.length > 0 ? (
                <MetricsPrefixSection
                  metricNames={scalarPartition.ungrouped}
                  gridProps={metricsGridProps}
                />
              ) : null}
              {scalarPartition.groups.map((group) => (
                <CollapsiblePrefixGroup key={group.key} title={group.key} count={group.items.length}>
                  <MetricsPrefixSection metricNames={group.items} gridProps={metricsGridProps} />
                </CollapsiblePrefixGroup>
              ))}
              {visibleMetrics.length === 0 ? (
                <EmptyState
                  icon={BarChart3}
                  title="No scalars visible"
                  description="All scalars are hidden. Click 'Show All' to display them."
                />
              ) : null}
            </>
          ) : (
            (() => {
              const artifactNames = visibleArtifactNamesForType(
                objectGroups,
                tab.id,
                hiddenArtifactIds
              );
              const partition = partitionNamesByPrefixForTab(artifactNames);

              return (
                <>
                  {partition.ungrouped.length > 0 ? (
                    <LoggedObjectsSection
                      {...loggedObjectsBaseProps}
                      artifactType={tab.id}
                      artifactNames={partition.ungrouped}
                    />
                  ) : null}
                  {partition.groups.map((group) => (
                    <CollapsiblePrefixGroup
                      key={group.key}
                      title={group.key}
                      count={group.items.length}
                    >
                      <LoggedObjectsSection
                        {...loggedObjectsBaseProps}
                        artifactType={tab.id}
                        artifactNames={group.items}
                      />
                    </CollapsiblePrefixGroup>
                  ))}
                </>
              );
            })()
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
