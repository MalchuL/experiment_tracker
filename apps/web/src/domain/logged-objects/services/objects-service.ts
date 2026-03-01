import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { ProjectObjectsResult } from "../types";

export interface GetProjectObjectsParams {
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  startTime?: string;
  endTime?: string;
}

function buildObjectsQuery(
  basePath: string,
  params?: GetProjectObjectsParams
): string {
  const searchParams = new URLSearchParams();
  searchParams.set("format", "objects");
  if (params?.experimentIds?.length) {
    for (const experimentId of params.experimentIds) {
      searchParams.append("experiment_id", experimentId);
    }
  }
  if (params?.objectTypes?.length) {
    for (const objectType of params.objectTypes) {
      searchParams.append("artifact_type", objectType);
    }
  }
  if (params?.names?.length) {
    for (const name of params.names) {
      searchParams.append("artifact_name", name);
    }
  }
  if (params?.startTime) {
    searchParams.set("start_time", params.startTime);
  }
  if (params?.endTime) {
    searchParams.set("end_time", params.endTime);
  }
  const query = searchParams.toString();
  return `${basePath}?${query}`;
}

export const loggedObjectsService = {
  getByProject: async (
    projectId: string,
    params?: GetProjectObjectsParams
  ): Promise<ProjectObjectsResult> => {
    const path = buildObjectsQuery(
      API_ROUTES.PROJECT_ARTIFACTS.BY_PROJECT.GET(projectId),
      params
    );
    const response = await serviceClients.api.get<ProjectObjectsResult>(path);
    return response.data;
  },
};
