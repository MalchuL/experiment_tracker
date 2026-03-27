export interface NamedExperimentArtifact {
  id: string;
  experimentId: string;
  name: string;
  filepath: string;
  filename: string;
  mimeType: string;
  storagePath: string;
  createdAt: string;
  updatedAt: string;
}

export type NamedArtifactPreview =
  | { status: "ok"; text: string; sizeBytes: number; contentType: string }
  | { status: "too_large"; message: string; sizeBytes: number; thresholdBytes: number; contentType: string }
  | { status: "binary"; message: string; sizeBytes: number; contentType: string }
  | { status: "decode_error"; message: string; sizeBytes: number; contentType: string };

