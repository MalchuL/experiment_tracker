"use client";

import { useMemo } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { ExperimentSidebar } from "@/components/shared/experiment-sidebar";
import { Button } from "@/components/ui/button";
import { useCurrentProject } from "@/domain/projects/hooks/project-provider";
import { Plus, FlaskConical, AlertCircle } from "lucide-react";
import {
    useExperiments,
    useReorderExperiments,
    useAggregatedMetrics,
    useSelectedExperimentStore,
} from "@/domain/experiments/hooks";
import { CreateExperimentDialog, ExperimentsTable } from "@/domain/experiments/components";

export default function Experiments() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const { experiments, isLoading: experimentsLoading } = useExperiments(projectId);
  const { aggregatedMetrics } = useAggregatedMetrics(projectId);
  const { reorderExperiments } = useReorderExperiments(projectId);


  // Filter metrics by displayMetrics setting
  const filteredMetrics = useMemo(() => {
    if (!project?.metrics) return [];
    const displayMetrics = project?.settings?.displayMetrics || [];
    if (displayMetrics.length === 0) return project.metrics;
    return project.metrics.filter(m => displayMetrics.includes(m.name));
  }, [project?.metrics, project?.settings?.displayMetrics]);

  const sortedExperiments = useMemo(() => {
    if (!experiments) return [];
    return [...experiments].sort((a, b) => a.order - b.order);
  }, [experiments]);

  const isLoading = projectLoading || experimentsLoading;

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its experiments.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Experiments" description="Loading..." />
        <ListSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description={`Experiments for "${project?.name}". Drag to reorder.`}
        actions={
          projectId ? (
            <CreateExperimentDialog
              projectId={projectId}
              projectName={project?.name}
            />
          ) : null
        }
      />

      {!sortedExperiments.length ? (
        <EmptyState
          icon={FlaskConical}
          title="No experiments yet"
          description="Create your first experiment to start tracking your research runs."
          action={
            projectId ? (
              <CreateExperimentDialog
                projectId={projectId}
                projectName={project?.name}
                trigger={
                  <Button data-testid="button-empty-create-experiment">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Experiment
                  </Button>
                }
              />
            ) : null
          }
        />
      ) : (
        <ExperimentsTable
          experiments={sortedExperiments}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={aggregatedMetrics}
          onExperimentClick={setSelectedExperimentId}
          onReorder={reorderExperiments}
        />
      )}

      {selectedExperimentId && (
        <ExperimentSidebar
          experimentId={selectedExperimentId}
          onClose={() => setSelectedExperimentId(null)}
          projectMetrics={filteredMetrics}
          aggregatedMetrics={aggregatedMetrics?.[selectedExperimentId] || undefined}
        />
      )}
    </div>
  );
}
