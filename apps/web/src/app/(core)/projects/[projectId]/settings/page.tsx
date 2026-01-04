"use client";

import { useCallback } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Settings, Eye } from "lucide-react";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { BasicInfoForm, NamingPatternForm, DisplayMetricsForm, MetricsManagement } from "@/domain/projects/components";
import { BasicInfoFormData, SettingsFormData } from "@/domain/projects/schemas";
import { ProjectMetric } from "@/domain/projects/types";
import { useToast } from "@/lib/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

export default function ProjectSettings() {
  const { project: currentProject, isLoading: projectLoading } = useCurrentProject();
  const projectId = currentProject?.id;
  const { project, isLoading, updateProject, updateIsPending } = useProject(projectId || "");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const handleUpdateSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
    if (projectId) {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.GET_BY_ID(projectId)] });
    }
    toast({
      title: "Settings saved",
      description: "Project settings have been updated successfully.",
    });
  }, [projectId, queryClient, toast]);

  const handleUpdateError = useCallback(() => {
    toast({
      title: "Error",
      description: "Failed to update project settings.",
      variant: "destructive",
    });
  }, [toast]);

  const handleBasicInfoSubmit = useCallback(
    (data: BasicInfoFormData) => {
      if (!projectId) return;
      updateProject(data, {
        onSuccess: handleUpdateSuccess,
        onError: handleUpdateError,
      });
    },
    [projectId, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  const handleSettingsSubmit = useCallback(
    (data: SettingsFormData) => {
      if (!projectId) return;
      updateProject(
        {
          settings: data,
        },
        {
          onSuccess: handleUpdateSuccess,
          onError: handleUpdateError,
        }
      );
    },
    [projectId, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  const handleAddMetric = useCallback(
    (metric: ProjectMetric) => {
      if (!project) return;
      updateProject(
        {
          metrics: [...project.metrics, metric],
        },
        {
          onSuccess: handleUpdateSuccess,
          onError: handleUpdateError,
        }
      );
    },
    [project, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  const handleRemoveMetric = useCallback(
    (metricName: string) => {
      if (!project) return;
      updateProject(
        {
          metrics: project.metrics.filter((m) => m.name !== metricName),
          settings: {
            ...project.settings,
            displayMetrics: project.settings.displayMetrics.filter((m) => m !== metricName),
          },
        },
        {
          onSuccess: handleUpdateSuccess,
          onError: handleUpdateError,
        }
      );
    },
    [project, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  const handleUpdateMetricDirection = useCallback(
    (metricName: string, direction: "maximize" | "minimize") => {
      if (!project) return;
      updateProject(
        {
          metrics: project.metrics.map((m) =>
            m.name === metricName ? { ...m, direction } : m
          ),
        },
        {
          onSuccess: handleUpdateSuccess,
          onError: handleUpdateError,
        }
      );
    },
    [project, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and access its settings.
        </p>
      </div>
    );
  }

  if (projectLoading || isLoading) {
    return <div className="p-6">Loading...</div>;
  }

  if (!project) {
    return <div className="p-6">Project not found</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Project Settings"
        description={`Configure settings for "${project.name}"`}
      />

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Project Information</CardTitle>
            <CardDescription>
              Update your project's basic details.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BasicInfoForm
              project={project}
              onSubmit={handleBasicInfoSubmit}
              isPending={updateIsPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Naming Pattern
            </CardTitle>
            <CardDescription>
              Configure how new experiments are named when derived from a parent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <NamingPatternForm
              project={project}
              onSubmit={handleSettingsSubmit}
              isPending={updateIsPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              Display Metrics
            </CardTitle>
            <CardDescription>
              Choose which metrics to show by default on the Scalars page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DisplayMetricsForm
              project={project}
              onSubmit={handleSettingsSubmit}
              isPending={updateIsPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tracked Metrics</CardTitle>
            <CardDescription>
              Add or remove metrics and set their optimization direction.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MetricsManagement
              project={project}
              onAddMetric={handleAddMetric}
              onRemoveMetric={handleRemoveMetric}
              onUpdateMetricDirection={handleUpdateMetricDirection}
              isPending={updateIsPending}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

