"use client";

import { AlertCircle } from "lucide-react";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { useScalarsPage } from "../hooks/use-scalars-page";
import { ScalarsPageActions } from "./scalars-page-actions";
import { ScalarExperimentsSidebar } from "./view-settings/scalar-experiments-sidebar";
import { ScalarViewSettingsSidebar } from "./view-settings/scalar-view-settings-sidebar";
import { ScalarsContentPanel } from "./scalars-content-panel";
import { ScalarsDialogs } from "./scalars-dialogs";
import { ScalarPointContextMenu } from "./metric-create/scalar-point-context-menu";
import { CreateMetricFromPointDialog } from "./metric-create/create-metric-from-point-dialog";

export function ScalarsPage() {
  const { project, loading, view, actions } = useScalarsPage();
  if (!project || !view)
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="max-w-md text-center text-muted-foreground">
          Click on the logo in the sidebar to select a project and view its
          metrics.
        </p>
      </div>
    );
  const pageActions = <ScalarsPageActions {...actions} />;
  if (loading)
    return (
      <div className="space-y-6 px-6 pt-6">
        <PageHeader
          title="Scalars"
          description="Compare scalars across experiments"
          actions={pageActions}
        />
        <ListSkeleton count={3} />
      </div>
    );
  return (
    <div className="flex h-full min-h-0 w-full min-w-0 gap-0">
      {actions.sidebars.experiments.open && (
        <ScalarExperimentsSidebar {...view.experiments} />
      )}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-3 pb-3 pt-3">
        <div className="mb-2">
          <PageHeader
            title="Scalars"
            description={`Scalars visualization for "${project.name}" - ${view.content.scalars.experiments.visibleExperiments.length} experiments visible`}
            actions={pageActions}
          />
        </div>
        <div className="min-h-0 flex-1 overflow-auto" data-scalar-scroll-root>
          <ScalarsContentPanel {...view.content} />
        </div>
      </div>
      {actions.sidebars.settings.open && (
        <ScalarViewSettingsSidebar {...view.settings} />
      )}
      <ScalarPointContextMenu {...view.pointMenu} />
      <CreateMetricFromPointDialog {...view.metricForm} />
      <ScalarsDialogs {...view.dialogs} />
    </div>
  );
}
