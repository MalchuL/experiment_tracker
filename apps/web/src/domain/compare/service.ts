import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { ExperimentSnapshotFilesResponse, SnapshotFileContent } from "./types";

export const compareService = {
  getSnapshotFiles: async (
    experimentIds: string[]
  ): Promise<ExperimentSnapshotFilesResponse> => {
    const response = await serviceClients.api.post<ExperimentSnapshotFilesResponse>(
      API_ROUTES.EXPERIMENTS.SNAPSHOT_FILES,
      { experimentIds }
    );
    return response.data;
  },

  getSnapshotFileContent: async (
    experimentId: string,
    file: { path: string; hash: string }
  ): Promise<SnapshotFileContent> => {
    const response = await serviceClients.api.post<SnapshotFileContent>(
      API_ROUTES.EXPERIMENTS.BY_ID.SNAPSHOT_FILE(experimentId),
      file
    );
    return response.data;
  },
};
