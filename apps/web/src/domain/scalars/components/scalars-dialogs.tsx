"use client";

import { RotateCcw } from "lucide-react";
import { ExperimentEditForm } from "@/components/shared/experiment-edit-form";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Experiment, UpdateExperiment } from "@/domain/experiments/types";
import type { ChartDomain } from "@/domain/scalars/types";
import { MetricChart } from "@/domain/scalars/components/metric-chart";

export interface ScalarsDialogsProps {
  fullscreenMetric: string | null;
  setFullscreenMetric: (metricName: string | null) => void;
  fullscreenMetricData: Array<Record<string, number | null>>;
  visibleExperiments: Experiment[];
  allExperiments: Experiment[];
  metricDomains: Record<string, ChartDomain>;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  onResetDomain: (metricName: string) => void;
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
        <DialogContent className="max-w-6xl w-[90vw] h-[80vh]">
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
                data={fullscreenMetricData}
                selectedExperiments={visibleExperiments}
                allExperiments={allExperiments}
                height={500}
                domain={metricDomains[fullscreenMetric] || { x: null, y: null }}
                onDomainChange={(domain) => onDomainChange(fullscreenMetric, domain)}
                isFullscreen={true}
              />
            )}
          </div>
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
