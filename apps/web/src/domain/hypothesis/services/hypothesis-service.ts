import { serviceClients } from "@/lib/api/clients/axios-client";
import { Hypothesis } from "../types";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { InsertHypothesis } from "../types/dto";


export interface HypothesisService {
    getRecent(projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]>;
    getByProject(projectId: string): Promise<Hypothesis[]>;
    createHypothesis(data: InsertHypothesis): Promise<Hypothesis>;
    deleteHypothesis(hypothesisId: string): Promise<void>;
}

export const hypothesisService: HypothesisService = {
    getRecent: async (projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]> => {
        const response = await serviceClients.api.get<Hypothesis[]>(API_ROUTES.HYPOTHESES.RECENT(projectId, limit, offset));
        return response.data;
    },
    getByProject: async (projectId: string): Promise<Hypothesis[]> => {
        const response = await serviceClients.api.get<Hypothesis[]>(API_ROUTES.PROJECTS.BY_ID.HYPOTHESES(projectId));
        return response.data;
    },
    createHypothesis: async (data: InsertHypothesis): Promise<Hypothesis> => {
        const response = await serviceClients.api.post<Hypothesis>(API_ROUTES.HYPOTHESES.CREATE, data);
        return response.data;
    },
    deleteHypothesis: async (hypothesisId: string): Promise<void> => {
        await serviceClients.api.delete(API_ROUTES.HYPOTHESES.BY_ID.DELETE(hypothesisId));
    },
};