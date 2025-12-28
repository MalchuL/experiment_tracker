import { apiRequest } from '../queryClient';
import { config } from '../config';
import type { Hypothesis, InsertHypothesis, Experiment } from '../../../../shared/schema';

export const hypothesesApi = {
  getAll: async (): Promise<Hypothesis[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/hypotheses`);
    return response.json();
  },

  getRecent: async (limit: number = 10): Promise<Hypothesis[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/hypotheses/recent?limit=${limit}`);
    return response.json();
  },

  getById: async (id: string): Promise<Hypothesis> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/hypotheses/${id}`);
    return response.json();
  },

  getExperiments: async (id: string): Promise<Experiment[]> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/hypotheses/${id}/experiments`);
    return response.json();
  },

  create: async (hypothesis: InsertHypothesis): Promise<Hypothesis> => {
    const response = await apiRequest('POST', `${config.API_BASE_URL}/api/hypotheses`, hypothesis);
    return response.json();
  },

  update: async (id: string, updates: Partial<InsertHypothesis>): Promise<Hypothesis> => {
    const response = await apiRequest('PATCH', `${config.API_BASE_URL}/api/hypotheses/${id}`, updates);
    return response.json();
  },

  delete: async (id: string): Promise<void> => {
    await apiRequest('DELETE', `${config.API_BASE_URL}/api/hypotheses/${id}`);
  },
};
