import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { HparamsCompareResponse } from "../types/hparams-compare";

export const hparamsCompareService = {
  compare: async (
    projectId: string,
    experimentIds: string[]
  ): Promise<HparamsCompareResponse> => {
    const response = await serviceClients.api.post<HparamsCompareResponse>(
      API_ROUTES.PROJECTS.BY_ID.HPARAMS_COMPARE(projectId),
      { experimentIds }
    );
    return response.data;
  },
};
