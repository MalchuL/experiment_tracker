"use client";

import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RightSidebarShell } from "@/components/shared/right-sidebar-shell";
import type {
  ArtifactViewItem,
  ChartDomain,
  SyncMode,
} from "@/domain/scalars/types";
import { ScalarDisplayControls } from "./scalar-display-controls";
import { ScalarSavedViewsSection } from "./scalar-saved-views-section";
import { ScalarVisibilityList } from "./scalar-visibility-list";
import { ViewSettingsSection } from "./view-settings-section";

interface ScalarViewSettingsSidebarProps {
  projectId?: string;
  currentQuery: string;
  syncMode: SyncMode;
  setSyncMode: (mode: SyncMode) => void;
  soloMode: boolean;
  onToggleSoloMode: () => void;
  cardHeight: number;
  setCardHeight: (value: number) => void;
  cardMinWidth: number;
  setCardMinWidth: (value: number) => void;
  hoverNameMaxLength: number;
  setHoverNameMaxLength: (value: number) => void;
  smoothing: number;
  onSmoothingChange: (value: number[]) => void;
  onSmoothingCommit: (value: number[]) => void;
  maxPointsPerPlot: number;
  maxArtifactStepsPerObject: number;
  dotThreshold: number;
  allLoggedMetricNames: string[];
  hiddenMetrics: Set<string>;
  artifactItems: ArtifactViewItem[];
  hiddenArtifactIds: Set<string>;
  metricDomains: Record<string, ChartDomain>;
  onToggleMetric: (metricName: string) => void;
  onShowAllMetrics: () => void;
  onShowOnlyMetric: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onResetMetricDomain: (metricName: string) => void;
  onToggleArtifact: (artifactId: string) => void;
  onOpenArtifact: (artifactId: string) => void;
  onResetAllDomains: () => void;
  onRestoreView: (query: string) => void;
  onClose?: () => void;
}

export function ScalarViewSettingsSidebar({
  projectId,
  currentQuery,
  syncMode,
  setSyncMode,
  soloMode,
  onToggleSoloMode,
  cardHeight,
  setCardHeight,
  cardMinWidth,
  setCardMinWidth,
  hoverNameMaxLength,
  setHoverNameMaxLength,
  smoothing,
  onSmoothingChange,
  onSmoothingCommit,
  maxPointsPerPlot,
  maxArtifactStepsPerObject,
  dotThreshold,
  allLoggedMetricNames,
  hiddenMetrics,
  artifactItems,
  hiddenArtifactIds,
  metricDomains,
  onToggleMetric,
  onShowAllMetrics,
  onShowOnlyMetric,
  onExpandMetric,
  onResetMetricDomain,
  onToggleArtifact,
  onOpenArtifact,
  onResetAllDomains,
  onRestoreView,
  onClose,
}: ScalarViewSettingsSidebarProps) {
  const hasZoom = Object.values(metricDomains).some((domain) => domain?.x || domain?.y);

  return (
    <RightSidebarShell
      title="View settings"
      onClose={onClose}
      variant="push"
      widthClassName="w-80"
      className="md:w-[320px] md:max-w-[320px]"
      testId="scalars-view-settings-sidebar"
      headerActions={
        hasZoom ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs"
            onClick={onResetAllDomains}
            data-testid="button-reset-all-zoom"
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Reset zoom
          </Button>
        ) : null
      }
    >
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-2 p-2.5">
          <ViewSettingsSection title="Controls">
            <ScalarDisplayControls
              syncMode={syncMode}
              setSyncMode={setSyncMode}
              soloMode={soloMode}
              onToggleSoloMode={onToggleSoloMode}
              cardHeight={cardHeight}
              setCardHeight={setCardHeight}
              cardMinWidth={cardMinWidth}
              setCardMinWidth={setCardMinWidth}
              hoverNameMaxLength={hoverNameMaxLength}
              setHoverNameMaxLength={setHoverNameMaxLength}
              smoothing={smoothing}
              onSmoothingChange={onSmoothingChange}
              onSmoothingCommit={onSmoothingCommit}
              maxPointsPerPlot={maxPointsPerPlot}
              maxArtifactStepsPerObject={maxArtifactStepsPerObject}
              dotThreshold={dotThreshold}
            />
          </ViewSettingsSection>

          <ViewSettingsSection title="Scalars and artifacts">
            <ScalarVisibilityList
              allLoggedMetricNames={allLoggedMetricNames}
              hiddenMetrics={hiddenMetrics}
              artifactItems={artifactItems}
              hiddenArtifactIds={hiddenArtifactIds}
              metricDomains={metricDomains}
              onToggleMetric={onToggleMetric}
              onShowAllMetrics={onShowAllMetrics}
              onShowOnlyMetric={onShowOnlyMetric}
              onExpandMetric={onExpandMetric}
              onResetMetricDomain={onResetMetricDomain}
              onToggleArtifact={onToggleArtifact}
              onOpenArtifact={onOpenArtifact}
            />
          </ViewSettingsSection>

          <ViewSettingsSection title="Saved views">
            <ScalarSavedViewsSection
              projectId={projectId}
              currentQuery={currentQuery}
              onRestoreView={onRestoreView}
            />
          </ViewSettingsSection>
        </div>
      </ScrollArea>
    </RightSidebarShell>
  );
}
