import type { Project, InsertProject, UpdateProject, DashboardStats } from '../types';
import type { Experiment } from '@/domain/experiments/types';
import type { Hypothesis } from '@/domain/hypothesis/types';
import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";


export interface ProjectsService {
  getAll: () => Promise<Project[]>;
  getById: (id: string) => Promise<Project>;
  getExperiments: (id: string) => Promise<Experiment[]>;
  getHypotheses: (id: string) => Promise<Hypothesis[]>;
  reorderExperiments: (id: string, experimentIds: string[]) => Promise<Experiment[]>;
  getMetrics: (id: string) => Promise<Record<string, Record<string, number | null>>>;
  create: (project: InsertProject) => Promise<Project>;
  update: (id: string, updates: UpdateProject) => Promise<Project>;
  delete: (id: string) => Promise<void>;
  getDashboardStats: (id: string) => Promise<DashboardStats>;
}

export const projectsService: ProjectsService = {
  getAll: async () => {
    const response = await serviceClients.api.get<Project[]>(API_ROUTES.PROJECTS.LIST);
    return response.data;
  },
  getById: async (id: string): Promise<Project> => {
    const response = await serviceClients.api.get<Project>(API_ROUTES.PROJECTS.BY_ID.GET(id));
    return response.data;
  },
  getExperiments: async (id: string): Promise<Experiment[]> => {
    const response = await serviceClients.api.get<Experiment[]>(API_ROUTES.PROJECTS.BY_ID.EXPERIMENTS(id));
    return response.data;
  },

  getHypotheses: async (id: string): Promise<Hypothesis[]> => {
    const response = await serviceClients.api.get<Hypothesis[]>(API_ROUTES.PROJECTS.BY_ID.HYPOTHESES(id));
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

  getMetrics: async (id: string): Promise<Record<string, Record<string, number | null>>> => {
    const response = await serviceClients.api.get<Record<string, Record<string, number | null>>>(API_ROUTES.PROJECTS.BY_ID.METRICS(id));
    return response.data;
  },

  getDashboardStats: async (id: string): Promise<DashboardStats> => {
    const response = await serviceClients.api.get<DashboardStats>(API_ROUTES.DASHBOARD.STATS(id));
    return response.data;
  },
};
