import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams, fetchAllPaginated } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginationParams } from "@/lib/types/pagination";
import type {
  LastLoggedExperimentsResult,
  ScalarNamesResult,
  ScalarsPointsResult,
} from "../types";

export interface GetProjectScalarsParams {
  experimentIds?: string[];
  scalarNames?: string[];
  maxPoints?: number;
  returnTags?: boolean;
  storeCache?: boolean;
  startTime?: string;
  endTime?: string;
  startStep?: number;
  endStep?: number;
}

export interface ScalarsService {
  getByProject: (
    projectId: string,
    params?: GetProjectScalarsParams & PaginationParams
  ) => Promise<ScalarsPointsResult>;
  getAllByProject: (
    projectId: string,
    params?: GetProjectScalarsParams
  ) => Promise<ScalarsPointsResult>;
  getByExperiment: (
    experimentId: string,
    params?: Omit<GetProjectScalarsParams, "experimentIds"> & PaginationParams
  ) => Promise<ScalarsPointsResult>;
  getLastLoggedByProject: (
    projectId: string,
    experimentIds?: string[]
  ) => Promise<LastLoggedExperimentsResult>;
  getNamesByProject: (projectId: string) => Promise<ScalarNamesResult>;
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
  if (params.scalarNames) {
    for (const scalarName of params.scalarNames) {
      searchParams.append("scalar_name", scalarName);
    }
  }
  if (params.maxPoints !== undefined) {
    searchParams.set("max_points", String(params.maxPoints));
  }
  if (params.returnTags !== undefined) {
    searchParams.set("return_tags", String(params.returnTags));
  }
  if (params.storeCache !== undefined) {
    searchParams.set("store_cache", String(params.storeCache));
  }
  if (params.startTime) {
    searchParams.set("start_time", params.startTime);
  }
  if (params.endTime) {
    searchParams.set("end_time", params.endTime);
  }
  if (params.startStep !== undefined) {
    searchParams.set("start_step", String(params.startStep));
  }
  if (params.endStep !== undefined) {
    searchParams.set("end_step", String(params.endStep));
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

  getAllByProject: async (projectId: string, params?: GetProjectScalarsParams) => {
    const data = await fetchAllPaginated((pagination) =>
      scalarsService.getByProject(projectId, {
        ...params,
        ...pagination,
      })
    );
    return {
      data,
      hasNext: false,
      size: data.length,
      total: data.length,
    };
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
    const data = await fetchAllPaginated((params) =>
      serviceClients.api
        .post<LastLoggedExperimentsResult>(
          API_ROUTES.SCALARS.BY_PROJECT.LAST_LOGGED(projectId),
          { experiment_ids: experimentIds ?? null },
          { params },
        )
        .then((response) => response.data)
    );
    return {
      data,
      hasNext: false,
      size: data.length,
      total: data.length,
    };
  },

  getNamesByProject: async (projectId: string) => {
    const response = await serviceClients.api.get<ScalarNamesResult>(
      API_ROUTES.SCALARS.BY_PROJECT.NAMES(projectId)
    );
    return response.data;
  },
};
