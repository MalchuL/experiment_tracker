"use client";

import { PageHeader } from "@/components/shared/page-header";

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
  return null;
}
