import { apiRequest } from '../queryClient';
import { config } from '../config';
import type { Experiment, InsertExperiment, Metric } from '../../../../shared/schema';

export const experimentsApi = {
  getAll: async (): Promise<Experiment[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/experiments`);
    return response.json();
  },

  getRecent: async (limit: number = 10): Promise<Experiment[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/experiments/recent?limit=${limit}`);
    return response.json();
  },

  getById: async (id: string): Promise<Experiment> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/experiments/${id}`);
    return response.json();
  },

  getMetrics: async (id: string): Promise<Metric[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/experiments/${id}/metrics`);
    return response.json();
  },

  create: async (experiment: InsertExperiment): Promise<Experiment> => {
    const response = await apiRequest('POST', `${config.API_BASE_URL}/api/experiments`, experiment);
    return response.json();
  },

  update: async (id: string, updates: Partial<InsertExperiment>): Promise<Experiment> => {
    const response = await apiRequest('PATCH', `${config.API_BASE_URL}/api/experiments/${id}`, updates);
    return response.json();
  },

  delete: async (id: string): Promise<void> => {
    await apiRequest('DELETE', `${config.API_BASE_URL}/api/experiments/${id}`);
  },
};
