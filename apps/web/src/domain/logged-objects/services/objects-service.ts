import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginationParams } from "@/lib/types/pagination";
import type { ArtifactsInfoResult } from "../types";

export interface GetProjectObjectsParams {
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  startTime?: string;
  endTime?: string;
}

function buildArtifactsQuery(
  basePath: string,
  params?: GetProjectObjectsParams & PaginationParams
): string {
  const searchParams = new URLSearchParams();
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
  return appendPaginationParams(query ? `${basePath}?${query}` : basePath, {
    limit: params?.limit ?? DEFAULT_PAGE_SIZE,
    offset: params?.offset,
  });
}

export const loggedObjectsService = {
  getByProject: async (
    projectId: string,
    params?: GetProjectObjectsParams & PaginationParams
  ): Promise<ArtifactsInfoResult> => {
    const path = buildArtifactsQuery(
      API_ROUTES.EXPERIMENT_ARTIFACTS.BY_PROJECT.GET_AT_STEP(projectId),
      params
    );
    const response = await serviceClients.api.get<ArtifactsInfoResult>(path);
    return response.data;
  },
};
