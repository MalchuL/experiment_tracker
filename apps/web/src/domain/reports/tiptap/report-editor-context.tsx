"use client";

import { createContext, useContext, type ReactNode } from "react";

export interface ReportEditorExperimentOption {
  id: string;
  name: string;
}

interface ReportEditorContextValue {
  projectId: string;
  experiments: ReportEditorExperimentOption[];
}

const ReportEditorContext = createContext<ReportEditorContextValue | null>(null);

export function ReportEditorProvider({
  projectId,
  experiments,
  children,
}: ReportEditorContextValue & { children: ReactNode }) {
  return (
    <ReportEditorContext.Provider value={{ projectId, experiments }}>
      {children}
    </ReportEditorContext.Provider>
  );
}

export function useReportEditorContext(): ReportEditorContextValue {
  const ctx = useContext(ReportEditorContext);
  if (!ctx) {
    throw new Error("useReportEditorContext must be used inside ReportEditorProvider");
  }
  return ctx;
}
