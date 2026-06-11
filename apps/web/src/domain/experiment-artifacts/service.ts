import { serviceClients } from "@/lib/api/clients/axios-client";
import { appendPaginationParams } from "@/lib/api/pagination";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { getAuthHeaders } from "@/domain/auth/utils/headers";
import { getPublicApiBaseUrl } from "@/lib/runtime-config";
import type { PaginatedResponse, PaginationParams } from "@/lib/types/pagination";
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
    names?: string[],
    pagination?: PaginationParams,
  ): Promise<PaginatedResponse<NamedExperimentArtifact>> => {
    const searchParams = new URLSearchParams();
    if (names?.length) {
      for (const name of names) {
        searchParams.append("name", name);
      }
    }
    const query = searchParams.toString();
    const path = appendPaginationParams(
      query
        ? `${API_ROUTES.EXPERIMENT_ARTIFACTS.LIST_BY_EXPERIMENT(experimentId)}?${query}`
        : API_ROUTES.EXPERIMENT_ARTIFACTS.LIST_BY_EXPERIMENT(experimentId),
      {
        limit: pagination?.limit ?? DEFAULT_PAGE_SIZE,
        offset: pagination?.offset,
      },
    );
    const response = await serviceClients.api.get<
      PaginatedResponse<NamedExperimentArtifactWire>
    >(path);
    return {
      ...response.data,
      data: response.data.data.map(normalizeArtifact),
    };
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
  deleteTrackedArtifact: async (experimentId: string, filepath: string): Promise<void> => {
    const path = API_ROUTES.EXPERIMENT_ARTIFACTS.DELETE(experimentId, filepath);
    await serviceClients.api.delete(path);
  },
  upsertTrackedArtifact: async (
    experimentId: string,
    file: File,
    options?: { name?: string; filepath?: string }
  ): Promise<NamedExperimentArtifact> => {
    const formData = new FormData();
    formData.append("experiment_id", experimentId);
    formData.append("filepath", options?.filepath?.trim() || file.name);
    const name = options?.name?.trim();
    if (name) {
      formData.append("name", name);
    }
    formData.append("file", file);

    const response = await fetch(
      `${getPublicApiBaseUrl()}${API_ROUTES.EXPERIMENT_ARTIFACTS.UPSERT}`,
      {
        method: "POST",
        body: formData,
        credentials: "include",
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      let message = `Upload failed (${response.status})`;
      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === "string") {
          message = body.detail;
        } else if (body.detail) {
          message = JSON.stringify(body.detail);
        }
      } catch {
        // keep default message
      }
      throw new Error(message);
    }

    const data = (await response.json()) as NamedExperimentArtifactWire;
    return normalizeArtifact(data);
  },
};

