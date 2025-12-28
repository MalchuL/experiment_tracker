import { apiRequest } from '../queryClient';
import { config } from '../config';
import type { DashboardStats } from '../../../../shared/schema';

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiRequest('GET', `${config.API_BASE_URL}/api/dashboard/stats`);
    return response.json();
  },
};
