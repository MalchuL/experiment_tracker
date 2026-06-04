import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { decodeUtf8Blob, filenameFromContentDisposition } from "./downloads";
import type {
  ExperimentSnapshotFiles,
  ExperimentSnapshotFilesResponse,
  SnapshotFile,
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

  downloadProjectArtifact: async (
    projectId: string,
    artifactHash: string
  ): Promise<Blob> => {
    const response = await serviceClients.api.get<Blob>(
      API_ROUTES.PROJECT_ARTIFACTS.DOWNLOAD(projectId, artifactHash),
      { responseType: "blob" }
    );
    return response.data;
  },

  /** Preview text via project CAS download (not POST .../data/snapshot/file). */
  getSnapshotFileContent: async (
    projectId: string,
    file: Pick<SnapshotFile, "path" | "hash">
  ): Promise<SnapshotFileContent> => {
    const blob = await compareService.downloadProjectArtifact(projectId, file.hash);
    const content = await decodeUtf8Blob(blob);
    return {
      path: file.path,
      hash: file.hash,
      content,
      size: blob.size,
    };
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
