import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { filenameFromContentDisposition } from "./downloads";
import type {
  ExperimentSnapshotFiles,
  ExperimentSnapshotFilesResponse,
  SnapshotFileContent,
} from "./types";

export interface SnapshotDownload {
  blob: Blob;
  filename: string;
}

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

  getExperimentSnapshotFiles: async (
    experimentId: string
  ): Promise<ExperimentSnapshotFiles> => {
    const response = await serviceClients.api.get<ExperimentSnapshotFiles>(
      API_ROUTES.EXPERIMENTS.BY_ID.SNAPSHOT_FILES(experimentId)
    );
    return response.data;
  },

  getSnapshotFileContent: async (
    experimentId: string,
    snapshotId: string,
    file: { path: string; hash: string }
  ): Promise<SnapshotFileContent> => {
    const response = await serviceClients.api.post<SnapshotFileContent>(
      API_ROUTES.EXPERIMENTS.BY_ID.SNAPSHOT_FILE_FOR_SNAPSHOT(experimentId, snapshotId),
      file
    );
    return response.data;
  },

  downloadExperimentSnapshot: async (
    experimentId: string,
    snapshotId?: string
  ): Promise<SnapshotDownload> => {
    const url = API_ROUTES.EXPERIMENTS.BY_ID.SNAPSHOT_DOWNLOAD(experimentId, snapshotId);
    const response = await serviceClients.api.get<Blob>(url, {
      responseType: "blob",
    });
    const fallback = `snapshot-${snapshotId ?? experimentId}.zip`;
    return {
      blob: response.data,
      filename: filenameFromContentDisposition(
        response.headers["content-disposition"],
        fallback
      ),
    };
  },
};
