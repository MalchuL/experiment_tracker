"use client";

import { useCallback, useState } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
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

const MIN_SIDEBAR_WIDTH = 240;
const MAX_SIDEBAR_WIDTH = 560;
const DEFAULT_SIDEBAR_WIDTH = 320;

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
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH);
  const hasZoom = Object.values(metricDomains).some((domain) => domain?.x || domain?.y);

  const handleResizeStart = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = sidebarWidth;

      const handlePointerMove = (moveEvent: PointerEvent) => {
        setSidebarWidth(
          Math.min(
            MAX_SIDEBAR_WIDTH,
            Math.max(MIN_SIDEBAR_WIDTH, startWidth + startX - moveEvent.clientX)
          )
        );
      };

      const handlePointerUp = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [sidebarWidth]
  );

  return (
    <RightSidebarShell
      title="View settings"
      onClose={onClose}
      variant="push"
      widthClassName=""
      className="md:max-w-none"
      style={{ width: sidebarWidth }}
      onResizePointerDown={handleResizeStart}
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
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="min-w-0 space-y-2 p-2.5">
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
      </div>
    </RightSidebarShell>
  );
}
