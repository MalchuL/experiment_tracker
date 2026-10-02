"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ScalarChartPoint,
  ChartDomain,
  ScalarHoverMode,
  ScalarPointSelection,
} from "../../types";
import { MetricChart } from "../metric-chart";

export interface ScalarFullscreenDialogProps {
  selection: {
    fullscreenMetric: string | null;
    setFullscreenMetric: (metricName: string | null) => void;
    fullscreenMetricData: ScalarChartPoint[];
  };
  experiments: {
    allExperiments: Experiment[];
    visibleExperiments: Experiment[];
  };
  zoom: {
    metricDomains: Record<string, ChartDomain>;
    onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
    onResetDomain: (metricName: string) => void;
  };
  display: {
    smoothing: number;
    dotThreshold: number;
    hoverMode: ScalarHoverMode;
    hoverNameMaxLength: number;
  };
  interactions: {
    onHoverModeChange: (mode: ScalarHoverMode) => void;
    onPointContextMenu: (
      point: ScalarPointSelection,
      position: { x: number; y: number },
    ) => void;
  };
}

export function ScalarFullscreenDialog({
  selection: { fullscreenMetric, setFullscreenMetric, fullscreenMetricData },
  experiments: { allExperiments, visibleExperiments },
  zoom: { metricDomains, onDomainChange, onResetDomain },
  display: { smoothing, dotThreshold, hoverMode, hoverNameMaxLength },
  interactions: { onHoverModeChange, onPointContextMenu },
}: ScalarFullscreenDialogProps) {
  return (
    <Dialog
      open={!!fullscreenMetric}
      onOpenChange={(open) => !open && setFullscreenMetric(null)}
    >
      <DialogContent className="flex h-[84vh] w-[96vw] max-w-[96vw] flex-col overflow-hidden p-3">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-4">
            <span>{fullscreenMetric}</span>
            <div className="flex items-center gap-2">
              {fullscreenMetric &&
                (metricDomains[fullscreenMetric]?.x ||
                  metricDomains[fullscreenMetric]?.y) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      fullscreenMetric && onResetDomain(fullscreenMetric)
                    }
                    data-testid="button-reset-zoom-fullscreen"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset Zoom
                  </Button>
                )}
            </div>
          </DialogTitle>
        </DialogHeader>
        <div className="min-h-0 flex-1">
          {fullscreenMetric && (
            <MetricChart
              metricName={fullscreenMetric}
              data={fullscreenMetricData}
              experiments={{
                selectedExperiments: visibleExperiments,
                allExperiments: allExperiments,
              }}
              viewport={{
                height: "100%",
                isFullscreen: true,
              }}
              zoom={{
                domain: metricDomains[fullscreenMetric] || { x: null, y: null },
                onDomainChange: (domain) =>
                  onDomainChange(fullscreenMetric, domain),
              }}
              display={{
                smoothing: smoothing,
                dotThreshold: dotThreshold,
                hoverMode: hoverMode,
                hoverNameMaxLength: hoverNameMaxLength,
              }}
              interactions={{
                onHoverModeChange: onHoverModeChange,
                onPointContextMenu: onPointContextMenu,
              }}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
