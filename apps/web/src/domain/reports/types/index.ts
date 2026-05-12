import type { JSONContent } from "@tiptap/react";

export type ReportDocumentJSON = JSONContent;

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
