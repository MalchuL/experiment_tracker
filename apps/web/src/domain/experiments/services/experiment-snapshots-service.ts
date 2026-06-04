import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";

export interface ExperimentSnapshot {
  experimentId: string;
  snapshotId: string | null;
  dataId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export const experimentSnapshotsService = {
  list: async (experimentIds: string[]): Promise<ExperimentSnapshot[]> => {
    const response = await serviceClients.api.post<ExperimentSnapshot[]>(
      API_ROUTES.EXPERIMENTS.SNAPSHOTS,
      { experimentIds }
    );
    return response.data;
  },

  delete: async (experimentId: string): Promise<ExperimentSnapshot> => {
    const response = await serviceClients.api.delete<ExperimentSnapshot>(
      API_ROUTES.EXPERIMENTS.BY_ID.DELETE_SNAPSHOT(experimentId)
    );
    return response.data;
  },
};
