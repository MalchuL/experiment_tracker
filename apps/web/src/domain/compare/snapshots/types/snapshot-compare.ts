export interface SnapshotFile {
  path: string;
  hash: string;
  size?: number | null;
}

export interface SnapshotFileContent {
  path: string;
  hash: string;
  content: string;
  size: number;
}

export interface ExperimentSnapshotFiles {
  experimentId: string;
  snapshotId: string | null;
  files: SnapshotFile[];
}

export interface ExperimentSnapshotFilesResponse {
  items: ExperimentSnapshotFiles[];
}
