import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { experimentsService } from "../services/experiments-service";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { Experiment, UpdateExperiment } from "../types";
import { useCallback } from "react";

export interface UseExperimentOptions {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export interface UseExperimentResult {
    experiment: Experiment | undefined;
    isLoading: boolean;
    updateIsPending: boolean;
    deleteIsPending: boolean;
    updateExperiment: (data: UpdateExperiment, options?: UseExperimentOptions) => Promise<Experiment>;
    deleteExperiment: (options?: UseExperimentOptions) => Promise<void>;
}

export function useExperiment(experimentId: string): UseExperimentResult {
    const { data: experiment, isLoading } = useQuery<Experiment>({
        queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(experimentId)],
        queryFn: () => experimentsService.get(experimentId),
        enabled: !!experimentId,
    });
    const queryClient = useQueryClient();
    const updateExperiment = useMutation({
        mutationFn: (experiment: Experiment) => experimentsService.update(experimentId, experiment),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(experimentId)] });
            if (experiment?.projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(experiment.projectId)] });
            }
        },
    });
    const deleteExperiment = useMutation({
        mutationFn: () => experimentsService.delete(experimentId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(experimentId)] });
            if (experiment?.projectId) {
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(experiment.projectId)] });
            }
        },
    });
    const updateFn = useCallback((data: UpdateExperiment, options?: UseExperimentOptions) => updateExperiment.mutateAsync(data as Experiment, options), [updateExperiment]);
    const deleteFn = useCallback((options?: UseExperimentOptions) => deleteExperiment.mutateAsync(undefined, options), [deleteExperiment]);
    return { experiment,
        isLoading,
        updateIsPending: updateExperiment.isPending,
        deleteIsPending: deleteExperiment.isPending,
        updateExperiment: updateFn,
        deleteExperiment: deleteFn,
    };
}