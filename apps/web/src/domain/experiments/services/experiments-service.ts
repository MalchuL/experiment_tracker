import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Experiment } from "../types";

export interface ExperimentsService {
    getRecent: (projectId: string, limit?: number | undefined, offset?: number | undefined) => Promise<Experiment[]>;
}

export const experimentsService: ExperimentsService = {
    getRecent: async (projectId: string, limit?: number | undefined, offset?: number | undefined) => {
        const response = await serviceClients.api.get<Experiment[]>(API_ROUTES.EXPERIMENTS.RECENT(projectId, limit, offset));
        return response.data;
    },
};