import { apiRequest } from '../queryClient';
import { config } from '../config';
import type { Metric, InsertMetric } from '../../../../shared/schema';

export const metricsApi = {
  create: async (metric: InsertMetric): Promise<Metric> => {
    const response = await apiRequest('POST', `${config.API_BASE_URL}/api/metrics`, metric);
    return response.json();
  },
};
