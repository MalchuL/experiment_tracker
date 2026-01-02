import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Metric } from "../types";

export interface MetricsService {
    getByExperiment: (experimentId: string) => Promise<Metric[]>;
}

export const metricsService = {
    getByExperiment: async (experimentId: string) => {
        const response = await serviceClients.api.get<Metric[]>(
            API_ROUTES.EXPERIMENTS.BY_ID.METRICS(experimentId)
        );
        return response.data;
    },
};