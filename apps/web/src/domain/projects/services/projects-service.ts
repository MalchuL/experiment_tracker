import type {
  DashboardStats,
  InsertProject,
  Project,
  ProjectSetting,
  UpdateProject,
} from "../types";
import type { Experiment } from "@/domain/experiments/types";
import type { Hypothesis } from "@/domain/hypothesis/types";
import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { Metric } from "@/domain/metrics/types";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";


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
  create: (project: InsertProject) => Promise<Project>;
  update: (id: string, updates: UpdateProject) => Promise<Project>;
  delete: (id: string) => Promise<void>;
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
    return response.data;
  },
  getById: async (id: string): Promise<Project> => {
    const response = await serviceClients.api.get<Project>(API_ROUTES.PROJECTS.BY_ID.GET(id));
    return response.data;
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
    return response.data;
  },

  update: async (id: string, updates: UpdateProject): Promise<Project> => {
    const response = await serviceClients.api.patch<Project>(API_ROUTES.PROJECTS.BY_ID.UPDATE(id), updates);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await serviceClients.api.delete(API_ROUTES.PROJECTS.BY_ID.DELETE(id));
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
