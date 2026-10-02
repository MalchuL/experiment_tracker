import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "@/domain/experiments/services";
import type {
  Experiment,
  InsertExperiment,
  UpdateExperiment,
} from "@/domain/experiments/types";
import { metricsService } from "@/domain/metrics/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import type { ScalarPointSelection } from "../types";

export function useScalarsDialogState(projectId?: string) {
  const [fullscreenMetric, setFullscreenMetric] = useState<string | null>(null);
  const [fullscreenArtifactId, setFullscreenArtifactId] = useState<
    string | null
  >(null);
  const [editExperiment, setEditExperiment] = useState<Experiment | null>(null);
  const [imagePreview, setImagePreview] = useState<{
    src: string;
    title: string;
  } | null>(null);
  const [metricPoint, setMetricPoint] = useState<ScalarPointSelection | null>(
    null,
  );
  const [createMetricOpen, setCreateMetricOpen] = useState(false);
  const [pointContext, setPointContext] = useState<{
    point: ScalarPointSelection;
    position: { x: number; y: number };
  } | null>(null);
  const queryClient = useQueryClient();
  const updateExperiment = useMutation({
    mutationFn: (payload: { id: string; data: UpdateExperiment }) =>
      experimentsService.update(
        payload.id,
        payload.data as unknown as InsertExperiment,
      ),
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
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.METRICS.GET(payload.experimentId)],
      });
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: [QUERY_KEYS.METRICS.BY_PROJECT(projectId)],
        });
      }
      setCreateMetricOpen(false);
      setMetricPoint(null);
    },
  });

  const handlePointContextMenu = (
    point: ScalarPointSelection,
    position: { x: number; y: number },
  ) => {
    setPointContext({ point, position });
  };

  return {
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
  };
}
