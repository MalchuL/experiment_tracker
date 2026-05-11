"use client";

import { useCallback, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Eye, Pencil, Plus, Settings, Trash2, X } from "lucide-react";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useProject } from "@/domain/projects/hooks/project-hook";
import {
  BasicInfoForm,
  DisplayMetricsForm,
  MetricsManagement,
  ProjectMembersPanel,
  ProjectDangerZone,
} from "@/domain/projects/components";
import { BasicInfoFormData } from "@/domain/projects/schemas";
import { ProjectDisplayMetric, ProjectMetric, ProjectSettingType } from "@/domain/projects/types";
import { displayMetricKeyEquals, displayMetricsForApiSave } from "@/lib/metrics/format-metric-label";
import { useToast } from "@/lib/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { projectsService } from "@/domain/projects/services";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface EditableSetting {
  originalName: string | null;
  name: string;
  description: string;
  type: ProjectSettingType;
  valueText: string;
  isEditing: boolean;
}

const SETTING_TYPES: ProjectSettingType[] = ["int", "float", "string", "boolean", "json"];

const toValueText = (type: ProjectSettingType, value: unknown): string => {
  if (type === "json") {
    return JSON.stringify(value ?? null, null, 2);
  }
  if (type === "boolean") {
    return value === true ? "true" : "false";
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
};

const parseSettingValue = (type: ProjectSettingType, raw: string): unknown => {
  const trimmed = raw.trim();
  if (type === "string") return raw;
  if (type === "int") {
    const parsed = Number.parseInt(trimmed, 10);
    if (Number.isNaN(parsed)) throw new Error("Value must be an integer.");
    return parsed;
  }
  if (type === "float") {
    const parsed = Number.parseFloat(trimmed);
    if (Number.isNaN(parsed)) throw new Error("Value must be a float.");
    return parsed;
  }
  if (type === "boolean") {
    if (trimmed === "true") return true;
    if (trimmed === "false") return false;
    throw new Error("Value must be true or false.");
  }
  try {
    return JSON.parse(trimmed || "null");
  } catch {
    throw new Error("Value must be valid JSON.");
  }
};

const formatValueForView = (type: ProjectSettingType, valueText: string): string => {
  if (!valueText.trim()) return "";
  if (type !== "json") return valueText;
  try {
    return JSON.stringify(JSON.parse(valueText), null, 2);
  } catch {
    return valueText;
  }
};

export default function ProjectSettings() {
  const { project: currentProject, isLoading: projectLoading } = useCurrentProject();
  const projectId = currentProject?.id;
  const { project, isLoading, updateProject, updateIsPending } = useProject(projectId);
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
    async (displayMetrics: ProjectDisplayMetric[]) => {
      if (!projectId || !project) return;
      try {
        await updateProject({
          metrics: {
            ...project.metrics,
            displayMetrics: displayMetricsForApiSave(project.metrics.trackedMetrics, displayMetrics),
          },
        });
        handleUpdateSuccess();
      } catch {
        handleUpdateError();
      }
    },
    [projectId, project, updateProject, handleUpdateSuccess, handleUpdateError]
  );

  const isSettingsBusy = updateIsPending;

  const handleAddMetric = useCallback(
    (metric: ProjectMetric) => {
      if (!project) return;
      updateProject(
        {
          metrics: {
            ...project.metrics,
            trackedMetrics: [...project.metrics.trackedMetrics, metric],
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

  const handleRemoveMetric = useCallback(
    (metric: ProjectMetric) => {
      if (!project) return;
      const target = { name: metric.name, label: metric.label ?? null };
      updateProject(
        {
          metrics: {
            trackedMetrics: project.metrics.trackedMetrics.filter(
              (m) => !displayMetricKeyEquals({ name: m.name, label: m.label }, target)
            ),
            displayMetrics: project.metrics.displayMetrics.filter((d) => {
              if (typeof d === "string") {
                if (metric.label != null && metric.label !== "") {
                  return true;
                }
                return d !== metric.name;
              }
              return !displayMetricKeyEquals({ name: d.name, label: d.label }, target);
            }),
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
    (metric: ProjectMetric, direction: "maximize" | "minimize") => {
      if (!project) return;
      updateProject(
        {
          metrics: {
            ...project.metrics,
            trackedMetrics: project.metrics.trackedMetrics.map((m) =>
              displayMetricKeyEquals({ name: m.name, label: m.label }, { name: metric.name, label: metric.label })
                ? { ...m, direction }
                : m
            ),
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
              Update your project&apos;s basic details.
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

        <ProjectMembersPanel projectId={projectId} />

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
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Tracked Metrics
            </CardTitle>
            <CardDescription>
              Add or remove metrics and set their optimization direction.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MetricsManagement
              project={project}
              projectId={projectId}
              onAddMetric={handleAddMetric}
              onRemoveMetric={handleRemoveMetric}
              onUpdateMetricDirection={handleUpdateMetricDirection}
              isPending={updateIsPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Custom Settings
            </CardTitle>
            <CardDescription>
              Add plugin and SDK settings as key/value entries.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <DynamicSettingsEditor
              key={`${projectId}-${JSON.stringify(project.settings)}`}
              projectId={projectId}
              initialSettings={project.settings}
              isBusy={isSettingsBusy}
              onSuccess={handleUpdateSuccess}
              onError={handleUpdateError}
            />
          </CardContent>
        </Card>

        <ProjectDangerZone projectId={projectId} />
      </div>
    </div>
  );
}

function DynamicSettingsEditor({
  projectId,
  initialSettings,
  isBusy,
  onSuccess,
  onError,
}: {
  projectId: string;
  initialSettings: {
    name: string;
    description: string;
    type: ProjectSettingType;
    value: unknown;
  }[];
  isBusy: boolean;
  onSuccess: () => void;
  onError: () => void;
}) {
  const { toast } = useToast();
  const [settingsDraft, setSettingsDraft] = useState<EditableSetting[]>(
    initialSettings.map((setting) => ({
      originalName: setting.name,
      name: setting.name,
      description: setting.description ?? "",
      type: setting.type,
      valueText: toValueText(setting.type, setting.value),
      isEditing: false,
    }))
  );

  const addSettingBlock = useCallback(() => {
    setSettingsDraft((prev) => [
      ...prev,
      {
        originalName: null,
        name: "",
        description: "",
        type: "string",
        valueText: "",
        isEditing: true,
      },
    ]);
  }, []);

  const updateDraft = useCallback((index: number, patch: Partial<EditableSetting>) => {
    setSettingsDraft((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item))
    );
  }, []);

  const saveSetting = useCallback(
    async (index: number) => {
      const draft = settingsDraft[index];
      if (!draft) return;
      if (!draft.name.trim()) {
        toast({
          title: "Invalid setting",
          description: "Setting name is required.",
          variant: "destructive",
        });
        return;
      }
      try {
        const parsedValue = parseSettingValue(draft.type, draft.valueText);
        if (!draft.originalName) {
          await projectsService.addSettings(projectId, {
            name: draft.name.trim(),
            description: draft.description || "",
            type: draft.type,
            value: parsedValue,
          });
        } else if (draft.originalName === draft.name.trim()) {
          await projectsService.updateSettingValue(projectId, draft.originalName, parsedValue);
        } else {
          await projectsService.deleteSetting(projectId, draft.originalName);
          await projectsService.addSettings(projectId, {
            name: draft.name.trim(),
            description: draft.description || "",
            type: draft.type,
            value: parsedValue,
          });
        }
        setSettingsDraft((prev) =>
          prev.map((item, idx) =>
            idx === index ? { ...item, originalName: draft.name.trim(), isEditing: false } : item
          )
        );
        onSuccess();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to save setting.";
        toast({
          title: "Error",
          description: message,
          variant: "destructive",
        });
      }
    },
    [projectId, settingsDraft, onSuccess, toast]
  );

  const removeSetting = useCallback(
    async (index: number) => {
      const draft = settingsDraft[index];
      if (!draft) return;
      try {
        if (draft.originalName) {
          await projectsService.deleteSetting(projectId, draft.originalName);
          onSuccess();
          return;
        }
        setSettingsDraft((prev) => prev.filter((_, idx) => idx !== index));
      } catch {
        onError();
      }
    },
    [projectId, settingsDraft, onSuccess, onError]
  );

  const setItemEditMode = useCallback((index: number, isEditing: boolean) => {
    setSettingsDraft((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, isEditing } : item))
    );
  }, []);

  const copyValue = useCallback(
    async (value: string) => {
      try {
        await navigator.clipboard.writeText(value);
        toast({
          title: "Copied",
          description: "Setting value copied to clipboard.",
        });
      } catch {
        toast({
          title: "Copy failed",
          description: "Unable to copy value to clipboard.",
          variant: "destructive",
        });
      }
    },
    [toast]
  );

  return (
    <>
      {!settingsDraft.length ? (
        <p className="text-sm text-muted-foreground">No custom settings yet.</p>
      ) : (
        settingsDraft.map((setting, index) => (
          <div
            key={`${setting.originalName ?? "new"}-${index}`}
            className="border rounded-md p-4 space-y-3"
          >
            {setting.isEditing ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Input
                    placeholder="name"
                    value={setting.name}
                    onChange={(e) => updateDraft(index, { name: e.target.value })}
                    disabled={isBusy}
                  />
                  <Input
                    placeholder="description (optional)"
                    value={setting.description}
                    onChange={(e) => updateDraft(index, { description: e.target.value })}
                    disabled={isBusy}
                  />
                </div>
                <Select
                  value={setting.type}
                  onValueChange={(value) =>
                    updateDraft(index, { type: value as ProjectSettingType })
                  }
                  disabled={isBusy}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {SETTING_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Textarea
                  placeholder="value"
                  value={setting.valueText}
                  onChange={(e) => updateDraft(index, { valueText: e.target.value })}
                  disabled={isBusy}
                />
              </>
            ) : (
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xl font-semibold leading-tight">{setting.name}</h4>
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setItemEditMode(index, true)}
                      disabled={isBusy}
                      data-testid={`button-edit-setting-${index}`}
                      aria-label="Edit setting"
                      title="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => void removeSetting(index)}
                      disabled={isBusy}
                      data-testid={`button-delete-setting-${index}`}
                      aria-label="Delete setting"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                {setting.description.trim() ? (
                  <p className="text-sm text-muted-foreground">{setting.description}</p>
                ) : null}
                <div className="space-y-1">
                  <button
                    type="button"
                    onClick={() => void copyValue(formatValueForView(setting.type, setting.valueText))}
                    className="w-full text-left rounded-md border bg-muted/30 p-3 hover:bg-muted/50 transition-colors"
                    title="Click to copy value"
                  >
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                      <code>
                        {formatValueForView(setting.type, setting.valueText) || "-"}
                      </code>
                    </pre>
                  </button>
                </div>
              </div>
            )}
            {setting.isEditing ? (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  onClick={() => void saveSetting(index)}
                  disabled={isBusy}
                  data-testid={`button-save-setting-${index}`}
                >
                  Save
                </Button>
                {setting.originalName && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setItemEditMode(index, false)}
                    disabled={isBusy}
                  >
                    <X className="w-4 h-4 mr-1" />
                    Cancel
                  </Button>
                )}
              </div>
            ) : null}
          </div>
        ))
      )}
      <Button
        type="button"
        variant="outline"
        onClick={addSettingBlock}
        disabled={isBusy}
        data-testid="button-add-setting-block"
      >
        <Plus className="w-4 h-4 mr-2" />
        Add Setting
      </Button>
    </>
  );
}

