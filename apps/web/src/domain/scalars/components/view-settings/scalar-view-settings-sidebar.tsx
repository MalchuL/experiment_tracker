"use client";

import { useCallback, useState, type ComponentProps } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RightSidebarShell } from "@/components/shared/right-sidebar-shell";
import {
  ScalarDisplayControls,
  type ScalarDisplayControlsProps,
} from "./scalar-display-controls";
import { ScalarSavedViewsSection } from "./scalar-saved-views-section";
import {
  ScalarVisibilityList,
  type ScalarVisibilityListProps,
} from "./scalar-visibility-list";
import { ViewSettingsSection } from "./view-settings-section";

const MIN_SIDEBAR_WIDTH = 240;
const MAX_SIDEBAR_WIDTH = 560;
const DEFAULT_SIDEBAR_WIDTH = 320;

interface ScalarViewSettingsSidebarProps {
  display: ScalarDisplayControlsProps;
  visibility: ScalarVisibilityListProps;
  views: ComponentProps<typeof ScalarSavedViewsSection>;
  zoom: { onResetAllDomains: () => void };
  onClose?: () => void;
}

export function ScalarViewSettingsSidebar({
  display,
  visibility,
  views,
  zoom,
  onClose,
}: ScalarViewSettingsSidebarProps) {
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH);
  const hasZoom = Object.values(visibility.scalars.metricDomains).some(
    (domain) => domain?.x || domain?.y,
  );

  const handleResizeStart = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = sidebarWidth;

      const handlePointerMove = (moveEvent: PointerEvent) => {
        setSidebarWidth(
          Math.min(
            MAX_SIDEBAR_WIDTH,
            Math.max(
              MIN_SIDEBAR_WIDTH,
              startWidth + startX - moveEvent.clientX,
            ),
          ),
        );
      };

      const handlePointerUp = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [sidebarWidth],
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
            onClick={zoom.onResetAllDomains}
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
            <ScalarDisplayControls {...display} />
          </ViewSettingsSection>

          <ViewSettingsSection title="Scalars and artifacts">
            <ScalarVisibilityList {...visibility} />
          </ViewSettingsSection>

          <ViewSettingsSection title="Saved views">
            <ScalarSavedViewsSection {...views} />
          </ViewSettingsSection>
        </div>
      </div>
    </RightSidebarShell>
  );
}
