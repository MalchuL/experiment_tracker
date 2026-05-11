/** Persisted report document from the API (camelCase). */
export interface ProjectReport {
  id: string;
  projectId: string;
  title: string;
  content: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectReportSummary {
  id: string;
  projectId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProjectReport {
  projectId: string;
  title: string;
  content?: Record<string, unknown>;
}

export interface UpdateProjectReport {
  title?: string;
  content?: Record<string, unknown>;
}
