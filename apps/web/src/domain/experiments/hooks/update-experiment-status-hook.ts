import { useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "@/domain/experiments/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { ExperimentStatusType } from "@/domain/experiments/types";
import { UpdateExperiment } from "@/domain/experiments/types/dto";

export interface UseUpdateExperimentStatusOptions {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export interface UseUpdateExperimentStatusResult {
  updateStatus: (
    experimentId: string,
    status: ExperimentStatusType,
    options?: UseUpdateExperimentStatusOptions
  ) => Promise<void>;
  isPending: boolean;
}

export function useUpdateExperimentStatus(
  projectId?: string
): UseUpdateExperimentStatusResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({
      experimentId,
      status,
    }: {
      experimentId: string;
      status: ExperimentStatusType;
    }) => {
      const updateData: UpdateExperiment = { status };
      return experimentsService.update(experimentId, updateData as any);
    },
    onSuccess: (_, variables) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(variables.experimentId)],
      });
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
        });
        queryClient.invalidateQueries({
          queryKey: [QUERY_KEYS.DASHBOARD.STATS(projectId)],
        });
      }
    },
  });

  return {
    updateStatus: async (
      experimentId: string,
      status: ExperimentStatusType,
      options?: UseUpdateExperimentStatusOptions
    ) => {
      try {
        await mutation.mutateAsync({ experimentId, status });
        options?.onSuccess?.();
      } catch (error) {
        options?.onError?.(error as Error);
        throw error;
      }
    },
    isPending: mutation.isPending,
  };
}

