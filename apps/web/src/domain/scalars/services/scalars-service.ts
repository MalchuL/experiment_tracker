import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginationParams } from "@/lib/types/pagination";
import type {
  LastLoggedExperimentsResult,
  ScalarsPointsResult,
} from "../types";

export interface GetProjectScalarsParams {
  experimentIds?: string[];
  maxPoints?: number;
  returnTags?: boolean;
  startTime?: string;
  endTime?: string;
}

export interface ScalarsService {
  getByProject: (
    projectId: string,
    params?: GetProjectScalarsParams & PaginationParams
  ) => Promise<ScalarsPointsResult>;
  getByExperiment: (
    experimentId: string,
    params?: Omit<GetProjectScalarsParams, "experimentIds"> & PaginationParams
  ) => Promise<ScalarsPointsResult>;
  getLastLoggedByProject: (
    projectId: string,
    experimentIds?: string[]
  ) => Promise<LastLoggedExperimentsResult>;
}

function buildScalarsQuery(
  basePath: string,
  params?: GetProjectScalarsParams & PaginationParams,
): string {
  if (!params) {
    return appendPaginationParams(basePath, { limit: DEFAULT_PAGE_SIZE });
  }
  const searchParams = new URLSearchParams();
  if (params.experimentIds?.length) {
    for (const experimentId of params.experimentIds) {
      searchParams.append("experiment_id", experimentId);
    }
  }
  if (params.maxPoints !== undefined) {
    searchParams.set("max_points", String(params.maxPoints));
  }
  if (params.returnTags !== undefined) {
    searchParams.set("return_tags", String(params.returnTags));
  }
  if (params.startTime) {
    searchParams.set("start_time", params.startTime);
  }
  if (params.endTime) {
    searchParams.set("end_time", params.endTime);
  }
  const query = searchParams.toString();
  return appendPaginationParams(query ? `${basePath}?${query}` : basePath, {
    limit: params.limit ?? DEFAULT_PAGE_SIZE,
    offset: params.offset,
  });
}

export const scalarsService: ScalarsService = {
  getByProject: async (
    projectId: string,
    params?: GetProjectScalarsParams & PaginationParams,
  ) => {
    const path = buildScalarsQuery(
      API_ROUTES.SCALARS.BY_PROJECT.GET(projectId),
      params
    );
    const response = await serviceClients.api.get<ScalarsPointsResult>(path);
    return response.data;
  },

  getByExperiment: async (
    experimentId: string,
    params?: Omit<GetProjectScalarsParams, "experimentIds"> & PaginationParams
  ) => {
    const path = buildScalarsQuery(
      API_ROUTES.SCALARS.BY_EXPERIMENT.GET(experimentId),
      params
    );
    const response = await serviceClients.api.get<ScalarsPointsResult>(path);
    return response.data;
  },

  getLastLoggedByProject: async (projectId: string, experimentIds?: string[]) => {
    const response = await serviceClients.api.post<LastLoggedExperimentsResult>(
      API_ROUTES.SCALARS.BY_PROJECT.LAST_LOGGED(projectId),
      { experiment_ids: experimentIds ?? null }
    );
    return response.data;
  },
};
