import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { ExperimentHparams, HparamsDocument } from "../types/hparams";

export const experimentHparamsService = {
  get: async (experimentId: string): Promise<ExperimentHparams> => {
    const response = await serviceClients.api.get<ExperimentHparams>(
      API_ROUTES.EXPERIMENTS.BY_ID.HPARAMS(experimentId)
    );
    return response.data;
  },
  replace: async (
    experimentId: string,
    hparams: HparamsDocument
  ): Promise<ExperimentHparams> => {
    const response = await serviceClients.api.put<ExperimentHparams>(
      API_ROUTES.EXPERIMENTS.BY_ID.HPARAMS(experimentId),
      { hparams }
    );
    return response.data;
  },
  delete: async (experimentId: string): Promise<ExperimentHparams> => {
    const response = await serviceClients.api.delete<ExperimentHparams>(
      API_ROUTES.EXPERIMENTS.BY_ID.HPARAMS(experimentId)
    );
    return response.data;
  },
};
