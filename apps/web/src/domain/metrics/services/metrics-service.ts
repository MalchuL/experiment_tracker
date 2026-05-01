import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginatedResponse } from "@/lib/types/pagination";
import { Metric } from "../types";

export interface MetricsService {
  getByExperiment: (experimentId: string) => Promise<Metric[]>;
  delete: (metricId: string) => Promise<void>;
  upsert: (payload: {
    experimentId: string;
    name: string;
    value: number;
    label?: string | null;
  }) => Promise<Metric>;
}

export const metricsService = {
  delete: async (metricId: string): Promise<void> => {
    await serviceClients.api.delete(API_ROUTES.METRICS.DELETE(metricId));
  },

  upsert: async (payload: {
    experimentId: string;
    name: string;
    value: number;
    label?: string | null;
  }): Promise<Metric> => {
    const response = await serviceClients.api.post<Metric>(API_ROUTES.METRICS.CREATE, payload);
    return response.data;
  },

  getByExperiment: async (experimentId: string) => {
    const metrics: Metric[] = [];
    let offset = 0;

    while (true) {
      const response = await serviceClients.api.get<PaginatedResponse<Metric>>(
        appendPaginationParams(API_ROUTES.EXPERIMENTS.BY_ID.METRICS(experimentId), {
          limit: DEFAULT_PAGE_SIZE,
          offset,
        })
      );
      metrics.push(...response.data.data);
      if (!response.data.hasNext) {
        return metrics;
      }
      offset += response.data.data.length;
    }
  },
};