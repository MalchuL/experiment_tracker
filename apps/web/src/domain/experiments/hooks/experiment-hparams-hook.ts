import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { experimentHparamsService } from "../services/experiment-hparams-service";
import type { HparamsDocument } from "../types/hparams";

export function useExperimentHparams(experimentId: string, enabled = true) {
  const queryClient = useQueryClient();
  const queryKey = [QUERY_KEYS.EXPERIMENTS.HPARAMS(experimentId)];
  const invalidateHparams = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey }),
      queryClient.invalidateQueries({
        predicate: (query) =>
          typeof query.queryKey[0] === "string" &&
          query.queryKey[0].includes("/hparams/list:"),
      }),
    ]);
  };
  const query = useQuery({
    queryKey,
    queryFn: () => experimentHparamsService.get(experimentId),
    enabled: enabled && Boolean(experimentId),
  });
  const replaceMutation = useMutation({
    mutationFn: (hparams: HparamsDocument) =>
      experimentHparamsService.replace(experimentId, hparams),
    onSuccess: invalidateHparams,
  });
  const deleteMutation = useMutation({
    mutationFn: () => experimentHparamsService.delete(experimentId),
    onSuccess: invalidateHparams,
  });

  return {
    ...query,
    replaceHparams: replaceMutation.mutateAsync,
    replacePending: replaceMutation.isPending,
    deleteHparams: deleteMutation.mutateAsync,
    deletePending: deleteMutation.isPending,
  };
}

export function useExperimentHparamsQuery(experimentId: string, enabled = true) {
  return useQuery({
    queryKey: [QUERY_KEYS.EXPERIMENTS.HPARAMS(experimentId)],
    queryFn: () => experimentHparamsService.get(experimentId),
    enabled: enabled && Boolean(experimentId),
  });
}
