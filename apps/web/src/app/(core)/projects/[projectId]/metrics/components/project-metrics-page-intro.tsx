"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info } from "lucide-react";

type ProjectMetricsPageIntroProps = {
  projectName: string | undefined;
};

/** Title and project name above the metrics grid. */
export function ProjectMetricsPageIntro({ projectName }: ProjectMetricsPageIntroProps) {
  return (
    <PageHeader
      title="Project metrics"
      description={projectName}
    />
  );
}

/** Short interaction hint at the bottom of the metrics column. */
export function ProjectMetricsPageUsageHint() {
  return (
    <Alert className="shrink-0 py-2">
      <Info className="h-4 w-4" />
      <AlertDescription className="text-sm">
        Click a metric value to cycle cell tints. Click an experiment (name) to open the side panel; the row is tinted
        with that color until the panel is closed.
      </AlertDescription>
    </Alert>
  );
}
