import { serviceClients } from "@/lib/api/clients/axios-client";
import { API_ROUTES } from "@/lib/constants/api-routes";
import type { NamedArtifactPreview, NamedExperimentArtifact } from "./types";

type NamedExperimentArtifactWire = {
  id: string;
  experiment_id?: string;
  experimentId?: string;
  name: string;
  filepath: string;
  filename: string;
  mime_type?: string;
  mimeType?: string;
  storage_path?: string;
  storagePath?: string;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
};

function normalizeArtifact(
  artifact: NamedExperimentArtifactWire
): NamedExperimentArtifact {
  return {
    id: artifact.id,
    experimentId: artifact.experimentId ?? artifact.experiment_id ?? "",
    name: artifact.name,
    filepath: artifact.filepath,
    filename: artifact.filename,
    mimeType: artifact.mimeType ?? artifact.mime_type ?? "application/octet-stream",
    storagePath: artifact.storagePath ?? artifact.storage_path ?? "",
    createdAt: artifact.createdAt ?? artifact.created_at ?? "",
    updatedAt: artifact.updatedAt ?? artifact.updated_at ?? "",
  };
}

export const experimentArtifactsService = {
  listByExperiment: async (
    experimentId: string,
    names?: string[]
  ): Promise<NamedExperimentArtifact[]> => {
    const params = new URLSearchParams();
    if (names?.length) {
      for (const name of names) {
        params.append("name", name);
      }
    }
    const query = params.toString();
    const path = query
      ? `${API_ROUTES.EXPERIMENT_ARTIFACTS.LIST_BY_EXPERIMENT(experimentId)}?${query}`
      : API_ROUTES.EXPERIMENT_ARTIFACTS.LIST_BY_EXPERIMENT(experimentId);
    const response = await serviceClients.api.get<NamedExperimentArtifactWire[]>(path);
    return response.data.map(normalizeArtifact);
  },
  previewNamedArtifact: async (
    experimentId: string,
    name: string,
    filepath: string,
    maxBytes = 2 * 1024 * 1024
  ): Promise<NamedArtifactPreview> => {
    const params = new URLSearchParams({
      experiment_id: experimentId,
      name,
      filepath,
      max_bytes: String(maxBytes),
    });
    const response = await fetch(`/api/experiment-artifacts/named/preview?${params.toString()}`, {
      method: "GET",
      cache: "no-store",
      credentials: "include",
    });
    const data = (await response.json()) as NamedArtifactPreview;
    return data;
  },
};

