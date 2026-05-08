import type {
  DashboardStats,
  InsertProject,
  Project,
  ProjectSetting,
  UpdateProject,
} from "../types";
import type { CategoryCleanupResponse, Experiment } from "@/domain/experiments/types";
import type { Hypothesis } from "@/domain/hypothesis/types";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type {
  Metric,
  MetricLabelsResponse,
  MetricsByLabelSnapshot,
  UniqueMetricDimensionsResponse,
} from "@/domain/metrics/types";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";
import { normalizeProject, normalizeProjectPage } from "../utils/normalize-project";


export interface ProjectsService {
  getAll: (params?: PaginationParams) => Promise<PaginatedResponse<Project>>;
  getById: (id: string) => Promise<Project>;
  getExperiments: (
    id: string,
    params?: PaginationParams,
  ) => Promise<PaginatedResponse<Experiment>>;
  getHypotheses: (
    id: string,
    params?: PaginationParams,
  ) => Promise<PaginatedResponse<Hypothesis>>;
  reorderExperiments: (id: string, experimentIds: string[]) => Promise<Experiment[]>;
  getMetrics: (
    id: string,
    params?: PaginationParams,
  ) => Promise<PaginatedResponse<Metric>>;
  getMetricLabels: (id: string) => Promise<MetricLabelsResponse>;
  getUniqueMetricDimensions: (id: string) => Promise<UniqueMetricDimensionsResponse>;
  getMetricsByLabelSnapshot: (
    id: string,
    args: {
      label: string;
      includeExperimentsWithoutMetrics: boolean;
      limit?: number;
      offset?: number;
    }
  ) => Promise<MetricsByLabelSnapshot>;
  create: (project: InsertProject) => Promise<Project>;
  update: (id: string, updates: UpdateProject) => Promise<Project>;
  delete: (id: string) => Promise<CategoryCleanupResponse>;
  getUsage: (id: string) => Promise<Record<string, unknown>>;
  cleanupCategory: (id: string, category: string) => Promise<CategoryCleanupResponse>;
  getDashboardStats: (id: string) => Promise<DashboardStats>;
  addSettings: (id: string, settings: ProjectSetting | ProjectSetting[]) => Promise<ProjectSetting[]>;
  getSettings: (id: string) => Promise<ProjectSetting[]>;
  getSettingsMap: (id: string) => Promise<Record<string, unknown>>;
  updateSettingValue: (id: string, name: string, value: unknown) => Promise<ProjectSetting>;
  deleteSetting: (id: string, name: string) => Promise<void>;
}

export const projectsService: ProjectsService = {
  getAll: async (params) => {
    const response = await serviceClients.api.get<PaginatedResponse<Project>>(
      appendPaginationParams(API_ROUTES.PROJECTS.LIST, params),
    );
    return normalizeProjectPage(response.data);
  },
  getById: async (id: string): Promise<Project> => {
    const response = await serviceClients.api.get<Project>(API_ROUTES.PROJECTS.BY_ID.GET(id));
    return normalizeProject(response.data);
  },
  getExperiments: async (
    id: string,
    params?: PaginationParams,
  ): Promise<PaginatedResponse<Experiment>> => {
    const response = await serviceClients.api.get<PaginatedResponse<Experiment>>(
      appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.EXPERIMENTS(id), params),
    );
    return response.data;
  },

  getHypotheses: async (
    id: string,
    params?: PaginationParams,
  ): Promise<PaginatedResponse<Hypothesis>> => {
    const response = await serviceClients.api.get<PaginatedResponse<Hypothesis>>(
      appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.HYPOTHESES(id), params),
    );
    return response.data;
  },

  create: async (project: InsertProject): Promise<Project> => {
    const response = await serviceClients.api.post<Project>(API_ROUTES.PROJECTS.CREATE, project);
    return normalizeProject(response.data);
  },

  update: async (id: string, updates: UpdateProject): Promise<Project> => {
    const response = await serviceClients.api.patch<Project>(API_ROUTES.PROJECTS.BY_ID.UPDATE(id), updates);
    return normalizeProject(response.data);
  },

  delete: async (id: string): Promise<CategoryCleanupResponse> => {
    const response = await serviceClients.api.delete<CategoryCleanupResponse>(
      API_ROUTES.PROJECTS.BY_ID.DELETE(id),
    );
    return response.data;
  },

  getUsage: async (id: string): Promise<Record<string, unknown>> => {
    const response = await serviceClients.api.get<Record<string, unknown>>(API_ROUTES.PROJECTS.BY_ID.USAGE(id));
    return response.data;
  },

  cleanupCategory: async (id: string, category: string): Promise<CategoryCleanupResponse> => {
    const response = await serviceClients.api.post<CategoryCleanupResponse>(
      API_ROUTES.PROJECTS.BY_ID.CLEANUP(id, category),
    );
    return response.data;
  },

  reorderExperiments: async (id: string, experimentIds: string[]): Promise<Experiment[]> => {
    const response = await serviceClients.api.patch<Experiment[]>(API_ROUTES.EXPERIMENTS.REORDER, { experimentIds });
    return response.data;
  },

  getMetrics: async (
    id: string,
    params?: PaginationParams,
  ): Promise<PaginatedResponse<Metric>> => {
    const response = await serviceClients.api.get<PaginatedResponse<Metric>>(
      appendPaginationParams(API_ROUTES.PROJECTS.BY_ID.METRICS(id), params),
    );
    return response.data;
  },

  getMetricLabels: async (id: string): Promise<MetricLabelsResponse> => {
    const response = await serviceClients.api.get<MetricLabelsResponse>(
      API_ROUTES.PROJECTS.BY_ID.METRIC_LABELS(id),
    );
    return response.data;
  },

  getUniqueMetricDimensions: async (id: string): Promise<UniqueMetricDimensionsResponse> => {
    const response = await serviceClients.api.get<UniqueMetricDimensionsResponse>(
      API_ROUTES.PROJECTS.BY_ID.METRICS_UNIQUE_DIMENSIONS(id),
    );
    return response.data;
  },

  getMetricsByLabelSnapshot: async (
    id: string,
    args: {
      label: string;
      includeExperimentsWithoutMetrics: boolean;
      limit?: number;
      offset?: number;
    },
  ): Promise<MetricsByLabelSnapshot> => {
    const params: Record<string, string | number | boolean> = {
      label: args.label,
      include_experiments_without_metrics: args.includeExperimentsWithoutMetrics,
    };
    if (args.limit != null) params.limit = args.limit;
    if (args.offset != null) params.offset = args.offset;
    const response = await serviceClients.api.get<MetricsByLabelSnapshot>(
      API_ROUTES.PROJECTS.BY_ID.METRICS_BY_LABEL(id),
      { params },
    );
    return response.data;
  },

  getDashboardStats: async (id: string): Promise<DashboardStats> => {
    const response = await serviceClients.api.get<DashboardStats>(API_ROUTES.DASHBOARD.STATS(id));
    return response.data;
  },
  addSettings: async (
    id: string,
    settings: ProjectSetting | ProjectSetting[]
  ): Promise<ProjectSetting[]> => {
    const response = await serviceClients.api.post<ProjectSetting[]>(
      API_ROUTES.PROJECTS.BY_ID.SETTINGS(id),
      settings
    );
    return response.data;
  },
  getSettings: async (id: string): Promise<ProjectSetting[]> => {
    const response = await serviceClients.api.get<ProjectSetting[]>(
      API_ROUTES.PROJECTS.BY_ID.SETTINGS(id)
    );
    return response.data;
  },
  getSettingsMap: async (id: string): Promise<Record<string, unknown>> => {
    const response = await serviceClients.api.get<Record<string, unknown>>(
      API_ROUTES.PROJECTS.BY_ID.SETTINGS_MAP(id)
    );
    return response.data;
  },
  updateSettingValue: async (
    id: string,
    name: string,
    value: unknown
  ): Promise<ProjectSetting> => {
    const response = await serviceClients.api.patch<ProjectSetting>(
      API_ROUTES.PROJECTS.BY_ID.SETTINGS_BY_NAME(id, name),
      { value }
    );
    return response.data;
  },
  deleteSetting: async (id: string, name: string): Promise<void> => {
    await serviceClients.api.delete(API_ROUTES.PROJECTS.BY_ID.SETTINGS_BY_NAME(id, name));
  },
};
