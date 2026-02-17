import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
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
    params?: GetProjectScalarsParams
  ) => Promise<ScalarsPointsResult>;
  getByExperiment: (
    experimentId: string,
    params?: Omit<GetProjectScalarsParams, "experimentIds">
  ) => Promise<ScalarsPointsResult>;
  getLastLoggedByProject: (
    projectId: string,
    experimentIds?: string[]
  ) => Promise<LastLoggedExperimentsResult>;
}

function buildScalarsQuery(
  basePath: string,
  params?: GetProjectScalarsParams
): string {
  if (!params) {
    return basePath;
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
  return query ? `${basePath}?${query}` : basePath;
}

export const scalarsService: ScalarsService = {
  getByProject: async (projectId: string, params?: GetProjectScalarsParams) => {
    const path = buildScalarsQuery(
      API_ROUTES.SCALARS.BY_PROJECT.GET(projectId),
      params
    );
    const response = await serviceClients.api.get<ScalarsPointsResult>(path);
    return response.data;
  },

  getByExperiment: async (
    experimentId: string,
    params?: Omit<GetProjectScalarsParams, "experimentIds">
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
