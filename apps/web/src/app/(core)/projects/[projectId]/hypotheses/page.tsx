"use client";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { Button } from "@/components/ui/button";
import { Lightbulb, Plus, AlertCircle } from "lucide-react";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useProjects } from "@/domain/projects/hooks";
import {
  useHypotheses,
  useDeleteHypothesis,
} from "@/domain/hypothesis/hooks";
import {
  CreateHypothesisDialog,
  HypothesesList,
} from "@/domain/hypothesis/components";

export default function Hypotheses() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { projects } = useProjects();
  const { hypotheses, isLoading: hypothesesLoading } = useHypotheses(projectId);
  const { deleteHypothesis } = useDeleteHypothesis(projectId);

  const isLoading = projectLoading || hypothesesLoading;

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its hypotheses.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Hypotheses" description="Manage your research hypotheses" />
        <ListSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hypotheses"
        description="Track and validate your research claims"
        actions={
          projectId ? (
            <CreateHypothesisDialog
              projectId={projectId}
              projects={projects}
            />
          ) : null
        }
      />

      {!hypotheses || hypotheses.length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="No hypotheses yet"
          description="Create your first hypothesis to track research claims and link them to experiments."
          action={
            projectId ? (
              <CreateHypothesisDialog
                projectId={projectId}
                projects={projects}
                trigger={
                  <Button data-testid="button-empty-create-hypothesis">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Hypothesis
                  </Button>
                }
              />
            ) : null
          }
        />
      ) : (
        <HypothesesList
          hypotheses={hypotheses}
          projectId={projectId}
          projects={projects}
          onDelete={deleteHypothesis}
        />
      )}
    </div>
  );
}
