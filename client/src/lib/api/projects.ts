import { apiRequest } from '../queryClient';
import { config } from '../config';
import type { Project, InsertProject, Experiment, Hypothesis } from '../../../../shared/schema';

export const projectsApi = {
  getAll: async (): Promise<Project[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/projects`);
    return response.json();
  },

  getById: async (id: string): Promise<Project> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/projects/${id}`);
    return response.json();
  },

  getExperiments: async (id: string): Promise<Experiment[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/projects/${id}/experiments`);
    return response.json();
  },

  getHypotheses: async (id: string): Promise<Hypothesis[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/projects/${id}/hypotheses`);
    return response.json();
  },

  create: async (project: InsertProject): Promise<Project> => {
    const response = await apiRequest('POST', `${config.API_BASE_URL}/api/projects`, project);
    return response.json();
  },

  update: async (id: string, updates: Partial<InsertProject>): Promise<Project> => {
    const response = await apiRequest('PATCH', `${config.API_BASE_URL}/api/projects/${id}`, updates);
    return response.json();
  },

  delete: async (id: string): Promise<void> => {
    await apiRequest('DELETE', `${config.API_BASE_URL}/api/projects/${id}`);
  },

  reorderExperiments: async (id: string, experimentIds: string[]): Promise<Experiment[]> => {
    const response = await apiRequest('PATCH', `${config.API_BASE_URL}/api/projects/${id}/experiments/reorder`, { experimentIds });
    return response.json();
  },

  getMetrics: async (id: string): Promise<Record<string, Record<string, number | null>>> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/projects/${id}/metrics`);
    return response.json();
  },
};
