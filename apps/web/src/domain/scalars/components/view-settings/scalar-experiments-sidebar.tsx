"use client";

import { useCallback, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Experiment } from "@/domain/experiments/types";
import { ScalarExperimentList } from "./scalar-experiment-list";

const MIN_SIDEBAR_WIDTH = 220;
const MAX_SIDEBAR_WIDTH = 520;
const DEFAULT_SIDEBAR_WIDTH = 288;

interface ScalarExperimentsSidebarProps {
  experiments: Experiment[];
  selectedExperimentIds: Set<string>;
  soloMode: boolean;
  chosenExperimentId: string | null;
  onSoloExperimentSelect: (id: string) => void;
  onToggleExperiment: (experimentId: string) => void;
  onSelectAllExperiments: () => void;
  onClearAllExperiments: () => void;
  onEditExperiment: (experiment: Experiment) => void;
  onClose?: () => void;
}

export function ScalarExperimentsSidebar({
  experiments,
  selectedExperimentIds,
  soloMode,
  chosenExperimentId,
  onSoloExperimentSelect,
  onToggleExperiment,
  onSelectAllExperiments,
  onClearAllExperiments,
  onEditExperiment,
  onClose,
}: ScalarExperimentsSidebarProps) {
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH);

  const handleResizeStart = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = sidebarWidth;

      const handlePointerMove = (moveEvent: PointerEvent) => {
        setSidebarWidth(
          Math.min(
            MAX_SIDEBAR_WIDTH,
            Math.max(MIN_SIDEBAR_WIDTH, startWidth + moveEvent.clientX - startX)
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
    <aside
      className="relative flex h-full min-h-0 shrink-0 flex-col border-r bg-background"
      data-testid="scalars-experiments-sidebar"
      style={{ width: sidebarWidth }}
    >
      <div className="flex shrink-0 items-center justify-between border-b p-3">
        <h2 className="truncate font-semibold">Experiments</h2>
        {onClose ? (
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 p-2.5">
        <ScalarExperimentList
          experiments={experiments}
          selectedExperimentIds={selectedExperimentIds}
          soloMode={soloMode}
          chosenExperimentId={chosenExperimentId}
          onSoloExperimentSelect={onSoloExperimentSelect}
          onToggleExperiment={onToggleExperiment}
          onSelectAllExperiments={onSelectAllExperiments}
          onClearAllExperiments={onClearAllExperiments}
          onEditExperiment={onEditExperiment}
        />
      </div>
      <button
        type="button"
        aria-label="Resize experiments sidebar"
        className="absolute right-0 top-0 h-full w-1 cursor-ew-resize bg-transparent transition-colors hover:bg-primary/30"
        onPointerDown={handleResizeStart}
      />
    </aside>
  );
}
