export type ReportDocumentJSON = Record<string, unknown>;

export interface ProjectReportSummary {
  id: string;
  projectId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectReport extends ProjectReportSummary {
  content: ReportDocumentJSON;
}

export interface CreateProjectReport {
  projectId: string;
  title: string;
  content?: ReportDocumentJSON;
}

export interface UpdateProjectReport {
  title?: string;
  content?: ReportDocumentJSON;
}
