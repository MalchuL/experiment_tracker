import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams, fetchAllPaginated } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginationParams } from "@/lib/types/pagination";
import type { ArtifactsInfoResult, ArtifactsInfoSummaryResult } from "../types";

export interface GetProjectObjectsParams {
  experimentIds?: string[];
  objectTypes?: string[];
  names?: string[];
  steps?: number[];
  maxSteps?: number;
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
  if (params?.steps?.length) {
    for (const step of params.steps) {
      searchParams.append("step", String(step));
    }
  }
  if (params?.startTime) {
    searchParams.set("start_time", params.startTime);
  }
  if (params?.endTime) {
    searchParams.set("end_time", params.endTime);
  }
  if (params?.maxSteps) {
    searchParams.set("max_steps", String(params.maxSteps));
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
  getSummaryByProject: async (
    projectId: string,
    params?: GetProjectObjectsParams & PaginationParams
  ): Promise<ArtifactsInfoSummaryResult> => {
    /** Lightweight names/types/steps payload used by scalars-page artifact sliders. */
    const path = buildArtifactsQuery(
      API_ROUTES.EXPERIMENT_ARTIFACTS.BY_PROJECT.SUMMARY_AT_STEP(projectId),
      params
    );
    const response = await serviceClients.api.get<ArtifactsInfoSummaryResult>(path);
    return response.data;
  },
  getAllSummaryByProject: async (
    projectId: string,
    params?: GetProjectObjectsParams
  ): Promise<ArtifactsInfoSummaryResult> => {
    const data = await fetchAllPaginated((pagination) =>
      loggedObjectsService.getSummaryByProject(projectId, {
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
  getDetailByProject: async (
    projectId: string,
    params: {
      experimentId: string;
      name: string;
      step: number;
      objectType?: string;
    }
  ): Promise<ArtifactsInfoResult> => {
    /** Full single-row metadata fetch used after an artifact slider step is selected. */
    const searchParams = new URLSearchParams({
      experiment_id: params.experimentId,
      artifact_name: params.name,
      step: String(params.step),
    });
    if (params.objectType) {
      searchParams.set("artifact_type", params.objectType);
    }
    const response = await serviceClients.api.get<ArtifactsInfoResult>(
      `${API_ROUTES.EXPERIMENT_ARTIFACTS.BY_PROJECT.DETAIL_AT_STEP(projectId)}?${searchParams.toString()}`
    );
    return response.data;
  },
};
