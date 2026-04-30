import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Experiment } from "../types";
import { InsertExperiment } from "@/shared/schema";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";

export interface ExperimentsService {
    getRecent: (
        projectId: string,
        params?: PaginationParams
    ) => Promise<PaginatedResponse<Experiment>>;
    getByProject: (
        projectId: string,
        params?: PaginationParams
    ) => Promise<PaginatedResponse<Experiment>>;
    getByProjectBatch: (
        projectId: string,
        experimentIds: string[]
    ) => Promise<PaginatedResponse<Experiment>>;
    create: (data: InsertExperiment) => Promise<Experiment>;
    reorder: (projectId: string, experimentIds: string[]) => Promise<Experiment[]>;
    get: (experimentId: string) => Promise<Experiment>;
    update: (experimentId: string, data: InsertExperiment) => Promise<Experiment>;
    delete: (experimentId: string) => Promise<void>;
}

export const experimentsService: ExperimentsService = {
    getRecent: async (projectId: string, params?: PaginationParams) => {
        const response = await serviceClients.api.get<PaginatedResponse<Experiment>>(
            appendPaginationParams(API_ROUTES.EXPERIMENTS.RECENT(projectId), params)
        );
        return response.data;
    },
    getByProject: async (projectId: string, params?: PaginationParams) => {
        const response = await serviceClients.api.get<PaginatedResponse<Experiment>>(
            appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.EXPERIMENTS(projectId), params)
        );
        return response.data;
    },
    getByProjectBatch: async (projectId: string, experimentIds: string[]) => {
        const response = await serviceClients.api.post<PaginatedResponse<Experiment>>(
            API_ROUTES.PROJECTS.BY_ID.EXPERIMENTS_BATCH(projectId),
            { experimentIds }
        );
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