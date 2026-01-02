import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Experiment } from "../types";
import { InsertExperiment } from "@/shared/schema";

export interface ExperimentsService {
    getRecent: (projectId: string, limit?: number | undefined, offset?: number | undefined) => Promise<Experiment[]>;
    getByProject: (projectId: string) => Promise<Experiment[]>;
    create: (data: InsertExperiment) => Promise<Experiment>;
    reorder: (projectId: string, experimentIds: string[]) => Promise<Experiment[]>;
    get: (experimentId: string) => Promise<Experiment>;
    update: (experimentId: string, data: InsertExperiment) => Promise<Experiment>;
    delete: (experimentId: string) => Promise<void>;
}

export const experimentsService: ExperimentsService = {
    getRecent: async (projectId: string, limit?: number | undefined, offset?: number | undefined) => {
        const response = await serviceClients.api.get<Experiment[]>(API_ROUTES.EXPERIMENTS.RECENT(projectId, limit, offset));
        return response.data;
    },
    getByProject: async (projectId: string) => {
        const response = await serviceClients.api.get<Experiment[]>(API_ROUTES.PROJECTS.BY_ID.EXPERIMENTS(projectId));
        return response.data;
    },
    create: async (data: InsertExperiment) => {
        const response = await serviceClients.api.post<Experiment>(API_ROUTES.EXPERIMENTS.CREATE, data);
        return response.data;
    },
    reorder: async (projectId: string, experimentIds: string[]) => {
        const response = await serviceClients.api.patch<Experiment[]>(
            API_ROUTES.PROJECTS.BY_ID.REORDER_EXPERIMENTS(projectId),
            { experimentIds }
        );
        return response.data;
    },

    get: async (experimentId: string) => {
        const response = await serviceClients.api.get<Experiment>(API_ROUTES.EXPERIMENTS.BY_ID.GET(experimentId));
        return response.data;
    },
    update: async (experimentId: string, data: InsertExperiment) => {
        const response = await serviceClients.api.patch<Experiment>(API_ROUTES.EXPERIMENTS.BY_ID.UPDATE(experimentId), data);
        return response.data;
    },
    delete: async (experimentId: string) => {
        await serviceClients.api.delete(API_ROUTES.EXPERIMENTS.BY_ID.DELETE(experimentId));
    },
};