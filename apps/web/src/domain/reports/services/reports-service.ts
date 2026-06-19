import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams, fetchAllPaginated } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";
import type {
  CreateProjectReport,
  ProjectReport,
  ProjectReportSummary,
  UpdateProjectReport,
} from "../types";

export interface ReportsService {
  listByProject(
    projectId: string,
    params?: PaginationParams,
  ): Promise<PaginatedResponse<ProjectReportSummary>>;
  listAllByProject(projectId: string): Promise<ProjectReportSummary[]>;
  getById(reportId: string): Promise<ProjectReport>;
  create(data: CreateProjectReport): Promise<ProjectReport>;
  update(reportId: string, data: UpdateProjectReport): Promise<ProjectReport>;
  delete(reportId: string): Promise<void>;
}

export const reportsService: ReportsService = {
  listByProject: async (projectId, params) => {
    const response = await serviceClients.api.get<
      PaginatedResponse<ProjectReportSummary>
    >(appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.REPORTS(projectId), params));
    return response.data;
  },
  listAllByProject: async (projectId) =>
    fetchAllPaginated(
      async (params) => {
        const response = await serviceClients.api.get<
          PaginatedResponse<ProjectReportSummary>
        >(appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.REPORTS(projectId), params));
        return response.data;
      },
      { limit: DEFAULT_PAGE_SIZE },
    ),
  getById: async (reportId) => {
    const response = await serviceClients.api.get<ProjectReport>(
      API_ROUTES.REPORTS.BY_ID.GET(reportId),
    );
    return response.data;
  },
  create: async (data) => {
    const response = await serviceClients.api.post<ProjectReport>(
      API_ROUTES.REPORTS.CREATE,
      data,
    );
    return response.data;
  },
  update: async (reportId, data) => {
    const response = await serviceClients.api.patch<ProjectReport>(
      API_ROUTES.REPORTS.BY_ID.PATCH(reportId),
      data,
    );
    return response.data;
  },
  delete: async (reportId) => {
    await serviceClients.api.delete(API_ROUTES.REPORTS.BY_ID.DELETE(reportId));
  },
};
