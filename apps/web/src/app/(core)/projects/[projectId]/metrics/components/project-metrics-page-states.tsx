"use client";

import { PageHeader } from "@/components/shared/page-header";
import { AlertCircle } from "lucide-react";

export function ProjectMetricsNoProject() {
  return (
    <div className="flex h-[40vh] flex-col items-center justify-center gap-4 px-6 text-muted-foreground">
      <AlertCircle className="h-10 w-10" aria-hidden />
      <p>Select a project from the logo menu.</p>
    </div>
  );
}

export function ProjectMetricsLoadingProject() {
  return (
    <div className="px-6 pt-6 text-sm text-muted-foreground">Loading project…</div>
  );
}

export function ProjectMetricsLabelListError() {
  return (
    <div className="px-6 pt-6 text-sm text-destructive">Could not load label list.</div>
  );
}

type ProjectMetricsNoLoggedMetricsProps = {
  projectName: string | undefined;
};

export function ProjectMetricsNoLoggedMetrics({ projectName }: ProjectMetricsNoLoggedMetricsProps) {
  return (
    <div className="space-y-4 px-6 pt-6">
      <PageHeader
        title="Project metrics"
        description={`${projectName} — no logged metrics with labels in this project yet.`}
      />
      <p className="text-sm text-muted-foreground">Log training metrics (with a label) to use this view.</p>
    </div>
  );
}
