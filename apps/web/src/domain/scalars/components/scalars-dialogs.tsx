"use client";

import { RotateCcw } from "lucide-react";
import { ExperimentEditForm } from "@/components/shared/experiment-edit-form";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Experiment, UpdateExperiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  LoggedObjectGroups,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
} from "@/domain/scalars/types";
import { MetricChart } from "@/domain/scalars/components/metric-chart";
import { LoggedObjectsSection } from "@/domain/scalars/components/logged-objects-section";
import type { Dispatch, SetStateAction } from "react";

export interface ScalarsDialogsProps {
  fullscreenMetric: string | null;
  setFullscreenMetric: (metricName: string | null) => void;
  fullscreenMetricData: ScalarChartPoint[];
  visibleExperiments: Experiment[];
  allExperiments: Experiment[];
  metricDomains: Record<string, ChartDomain>;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  onResetDomain: (metricName: string) => void;
  smoothing: number;
  dotThreshold: number;
  hoverMode: ScalarHoverMode;
  onPointContextMenu: (point: ScalarPointSelection, position: { x: number; y: number }) => void;
  fullscreenArtifactId: string | null;
  setFullscreenArtifactId: (artifactId: string | null) => void;
  objectGroups: LoggedObjectGroups;
  cardMinWidth: number;
  cardHeight: number;
  objectStepSelection: Record<string, number>;
  setObjectStepSelection: Dispatch<SetStateAction<Record<string, number>>>;
  debouncedObjectStepSelection: Record<string, number>;
  experimentStepOverrideEnabled: Record<string, boolean>;
  setExperimentStepOverrideEnabled: Dispatch<SetStateAction<Record<string, boolean>>>;
  experimentStepOverrides: Record<string, number>;
  setExperimentStepOverrides: Dispatch<SetStateAction<Record<string, number>>>;
  debouncedExperimentStepOverrides: Record<string, number>;
  imagePreview: { src: string; title: string } | null;
  setImagePreview: (value: { src: string; title: string } | null) => void;
  editExperiment: Experiment | null;
  setEditExperiment: (experiment: Experiment | null) => void;
  isSavingExperiment: boolean;
  onSaveExperiment: (payload: { id: string; data: UpdateExperiment }, onSuccess: () => void) => void;
}

export function ScalarsDialogs({
  fullscreenMetric,
  setFullscreenMetric,
  fullscreenMetricData,
  visibleExperiments,
  allExperiments,
  metricDomains,
  onDomainChange,
  onResetDomain,
  smoothing,
  dotThreshold,
  hoverMode,
  onPointContextMenu,
  fullscreenArtifactId,
  setFullscreenArtifactId,
  objectGroups,
  cardMinWidth,
  cardHeight,
  objectStepSelection,
  setObjectStepSelection,
  debouncedObjectStepSelection,
  experimentStepOverrideEnabled,
  setExperimentStepOverrideEnabled,
  experimentStepOverrides,
  setExperimentStepOverrides,
  debouncedExperimentStepOverrides,
  imagePreview,
  setImagePreview,
  editExperiment,
  setEditExperiment,
  isSavingExperiment,
  onSaveExperiment,
}: ScalarsDialogsProps) {
  return (
    <>
      <Dialog open={!!fullscreenMetric} onOpenChange={(open) => !open && setFullscreenMetric(null)}>
        <DialogContent className="max-w-[96vw] w-[96vw] h-[84vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between gap-4">
              <span>{fullscreenMetric}</span>
              <div className="flex items-center gap-2">
                {fullscreenMetric && (metricDomains[fullscreenMetric]?.x || metricDomains[fullscreenMetric]?.y) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fullscreenMetric && onResetDomain(fullscreenMetric)}
                    data-testid="button-reset-zoom-fullscreen"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset Zoom
                  </Button>
                )}
              </div>
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            {fullscreenMetric && (
              <MetricChart
                metricName={fullscreenMetric}
                data={fullscreenMetricData}
                selectedExperiments={visibleExperiments}
                allExperiments={allExperiments}
                height={620}
                domain={metricDomains[fullscreenMetric] || { x: null, y: null }}
                smoothing={smoothing}
                dotThreshold={dotThreshold}
                hoverMode={hoverMode}
                onPointContextMenu={onPointContextMenu}
                onDomainChange={(domain) => onDomainChange(fullscreenMetric, domain)}
                isFullscreen={true}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!fullscreenArtifactId}
        onOpenChange={(open) => !open && setFullscreenArtifactId(null)}
      >
        <DialogContent className="max-w-[96vw] w-[96vw] h-[86vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Artifact view</DialogTitle>
          </DialogHeader>
          {fullscreenArtifactId ? (
            <LoggedObjectsSection
              objectGroups={objectGroups}
              visibleExperiments={visibleExperiments}
              cardMinWidth={Math.max(cardMinWidth, 420)}
              cardHeight={Math.max(cardHeight, 420)}
              objectStepSelection={objectStepSelection}
              setObjectStepSelection={setObjectStepSelection}
              debouncedObjectStepSelection={debouncedObjectStepSelection}
              experimentStepOverrideEnabled={experimentStepOverrideEnabled}
              setExperimentStepOverrideEnabled={setExperimentStepOverrideEnabled}
              experimentStepOverrides={experimentStepOverrides}
              setExperimentStepOverrides={setExperimentStepOverrides}
              debouncedExperimentStepOverrides={debouncedExperimentStepOverrides}
              onImagePreview={setImagePreview}
              onlyArtifactId={fullscreenArtifactId}
            />
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={!!imagePreview} onOpenChange={(open) => !open && setImagePreview(null)}>
        <DialogContent className="max-w-6xl w-[92vw] h-[88vh]">
          <DialogHeader>
            <DialogTitle>{imagePreview?.title ?? "Image preview"}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 flex items-center justify-center">
            {imagePreview && (
              <img
                src={imagePreview.src}
                alt={imagePreview.title}
                className="max-h-[76vh] max-w-full object-contain rounded"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editExperiment} onOpenChange={(open) => !open && setEditExperiment(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Experiment</DialogTitle>
          </DialogHeader>
          {editExperiment && (
            <ExperimentEditForm
              experiment={editExperiment}
              isSaving={isSavingExperiment}
              onSave={(data) => {
                onSaveExperiment(
                  {
                    id: editExperiment.id,
                    data: {
                      name: data.name,
                      description: data.description,
                      color: data.color,
                    },
                  },
                  () => setEditExperiment(null)
                );
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
