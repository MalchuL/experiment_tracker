import { serviceClients } from "@/lib/api/clients/axios-client";
import { Hypothesis } from "../types";
import { API_ROUTES } from "@/lib/constants/api-routes";


export interface HypothesisService {
    getRecent(projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]>;
}

export const hypothesisService: HypothesisService = {
    getRecent: async (projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]> => {
        const response = await serviceClients.api.get<Hypothesis[]>(API_ROUTES.HYPOTHESES.RECENT(projectId, limit, offset));
        return response.data;
    }
};