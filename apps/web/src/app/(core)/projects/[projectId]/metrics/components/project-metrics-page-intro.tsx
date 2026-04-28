"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { formatMetricLabel } from "@/lib/metrics/format-metric-label";
import { Info } from "lucide-react";

type ProjectMetricsPageIntroProps = {
  projectName: string | undefined;
  editMode: boolean;
};

/** Title, description, and usage alert above the metrics grid. */
export function ProjectMetricsPageIntro({ projectName, editMode }: ProjectMetricsPageIntroProps) {
  return (
    <div className="shrink-0 space-y-3">
      <PageHeader
        title="Project metrics"
        description={`${projectName} — pivot by label; ${formatMetricLabel("loss", "a")} matches project settings keys.`}
      />
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription className="text-sm space-y-1.5">
          <p>
            Click a metric value to cycle cell tints. Click an experiment (name) to open the side panel; the row is
            tinted with that color until the panel is closed. In <strong>report</strong> mode, use
            <strong> Download</strong> to save the current table (visible columns, current sort) as CSV, as JSON (an
            array of rows: header row first, then each data row), or as a Markdown pipe table.
          </p>
          {editMode ? (
            <p>
              <span className="font-medium">Col</span> (every column, including{" "}
              <span className="font-mono">experimentId</span> / <span className="font-mono">createdAt</span>) and, on
              metric columns only, <span className="font-medium">Min</span> / <span className="font-medium">Max</span>,
              control the off-edit report.
            </p>
          ) : null}
        </AlertDescription>
      </Alert>
    </div>
  );
}
