import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { HparamsListResponse } from "../types/hparams-list";

export const hparamsListService = {
  list: async (
    projectId: string,
    experimentIds: string[]
  ): Promise<HparamsListResponse> => {
    const response = await serviceClients.api.post<HparamsListResponse>(
      API_ROUTES.PROJECTS.BY_ID.HPARAMS_LIST(projectId),
      { experimentIds }
    );
    return response.data;
  },
};
