import { serviceClients } from "@/lib/api/clients/axios-client";
import { Hypothesis } from "../types";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { InsertHypothesis } from "../types/dto";
import type { PaginatedResponse } from "@/lib/types/pagination";
import { appendPaginationParams, fetchAllPaginated } from "@/lib/api/pagination";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";


export interface HypothesisService {
    getRecent(projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]>;
    getByProject(projectId: string): Promise<Hypothesis[]>;
    createHypothesis(data: InsertHypothesis): Promise<Hypothesis>;
    deleteHypothesis(hypothesisId: string): Promise<void>;
}

export const hypothesisService: HypothesisService = {
    getRecent: async (projectId: string, limit?: number | undefined, offset?: number | undefined): Promise<Hypothesis[]> => {
        const response = await serviceClients.api.get<PaginatedResponse<Hypothesis>>(
            API_ROUTES.HYPOTHESES.RECENT(projectId, limit, offset)
        );
        return response.data.data;
    },
    getByProject: async (projectId: string): Promise<Hypothesis[]> => {
        return fetchAllPaginated(
            async (params) => {
                const response = await serviceClients.api.get<PaginatedResponse<Hypothesis>>(
                    appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.HYPOTHESES(projectId), params)
                );
                return response.data;
            },
            { limit: DEFAULT_PAGE_SIZE },
        );
    },
    createHypothesis: async (data: InsertHypothesis): Promise<Hypothesis> => {
        const response = await serviceClients.api.post<Hypothesis>(API_ROUTES.HYPOTHESES.CREATE, data);
        return response.data;
    },
    deleteHypothesis: async (hypothesisId: string): Promise<void> => {
        await serviceClients.api.delete(API_ROUTES.HYPOTHESES.BY_ID.DELETE(hypothesisId));
    },
};
