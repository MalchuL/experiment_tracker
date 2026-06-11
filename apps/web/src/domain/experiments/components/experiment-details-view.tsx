"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { EntityIdDisplay } from "@/components/shared/entity-id-display";
import {
  ExperimentEditForm,
  type ExperimentEditSavePayload,
} from "@/components/shared/experiment-edit-form";
import { ExperimentFeaturesPanel } from "@/components/shared/experiment-features-panel";
import { ExperimentHparamsPanel } from "@/components/shared/experiment-hparams-panel";
import { ExperimentSidebarLoggedMetrics } from "@/components/shared/experiment-sidebar-logged-metrics";
import { MetricNameValueDiffRow } from "@/components/shared/metric-name-value-diff-row";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExperimentArtifactsPanel } from "@/domain/experiment-artifacts/components/experiment-artifacts-panel";
import { ExperimentDangerZoneCard } from "@/domain/experiments/components/experiment-danger-zone-card";
import { ExperimentTagsEditor } from "@/domain/experiments/components/experiment-tags-editor";
import {
  useAggregatedMetrics,
  useExperiment,
  useExperiments,
} from "@/domain/experiments/hooks";
import { experimentMatchesSearch } from "@/domain/experiments/lib/experiment-matches-search";
import type { ExperimentSnapshot } from "@/domain/experiments/services";
import { experimentSnapshotsService, experimentsService } from "@/domain/experiments/services";
import type { Experiment } from "@/domain/experiments/types";
import type { UpdateExperiment } from "@/domain/experiments/types/dto";
import type { Metric } from "@/domain/metrics/types";
import { useExperimentMetrics } from "@/domain/metrics/hooks";
import { metricsService } from "@/domain/metrics/services/metrics-service";
import { useProject } from "@/domain/projects/hooks/project-hook";
import type { Project } from "@/domain/projects/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { decodeStringSelection } from "@/domain/scalars/utils/selection-codec";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import {
  displayMetricKeyEquals,
  formatMetricLabel,
  getDisplayedTrackedMetrics,
  projectMetricKeyString,
} from "@/lib/metrics/format-metric-label";
import { ChevronDown, GitBranch, Trash2, X } from "lucide-react";
import { format, parseISO } from "date-fns";

type DetailsTab = "overview" | "metrics" | "artifacts" | "hparams" | "features";

const DETAILS_TABS: DetailsTab[] = ["overview", "metrics", "artifacts", "hparams", "features"];

function parseDetailsTab(raw: string | null): DetailsTab {
  if (raw && DETAILS_TABS.includes(raw as DetailsTab)) {
    return raw as DetailsTab;
  }
  return "overview";
}

function formatExperimentParentOption(exp: Pick<Experiment, "name" | "id">): string {
  return `${exp.name} (${exp.id.slice(0, 7)})`;
}

export function ExperimentDetailsView({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const experimentIdsOrdered = useMemo(
    () => decodeStringSelection(searchParams.get("exp")),
    [searchParams]
  );

  const activeTab = useMemo(
    () => parseDetailsTab(searchParams.get("detailsTab")),
    [searchParams]
  );

  const metricsTabActive = activeTab === "metrics";
  const artifactsTabActive = activeTab === "artifacts";
  const featuresTabActive = activeTab === "features";

  const { experiments: projectExperiments } = useExperiments(projectId, {
    includeFeatures: featuresTabActive,
  });
  const { project } = useProject(projectId);
  const { aggregatedMetricsByExperiment } = useAggregatedMetrics(projectId);

  const experimentsOrdered = useMemo(() => {
    const map = new Map(projectExperiments.map((e) => [e.id, e]));
    return experimentIdsOrdered.map((id) => map.get(id)).filter((e): e is Experiment => !!e);
  }, [projectExperiments, experimentIdsOrdered]);

  const primaryExperimentId = experimentIdsOrdered[0] ?? "";
  const primaryExperiment = experimentsOrdered[0];

  const parentExperimentIdForFeatures =
    featuresTabActive && primaryExperiment?.parentExperimentId
      ? primaryExperiment.parentExperimentId
      : "";
  const { experiment: savedParentExperiment } = useExperiment(parentExperimentIdForFeatures);

  const metricsQueries = useQueries({
    queries: experimentIdsOrdered.map((experimentId) => ({
      queryKey: [QUERY_KEYS.METRICS.GET(experimentId)],
      queryFn: () => metricsService.getByExperiment(experimentId),
      enabled: experimentIdsOrdered.length > 0 && metricsTabActive,
    })),
  });

  const snapshotsQuery = useQuery({
    queryKey: [QUERY_KEYS.EXPERIMENTS.SNAPSHOTS(experimentIdsOrdered)],
    queryFn: () => experimentSnapshotsService.list(experimentIdsOrdered),
    enabled: experimentIdsOrdered.length > 0,
  });

  const snapshotsByExperiment = useMemo(() => {
    return new Map((snapshotsQuery.data ?? []).map((snapshot) => [snapshot.experimentId, snapshot]));
  }, [snapshotsQuery.data]);

  const updateExperimentMutation = useMutation({
    mutationFn: async ({
      experimentId,
      payload,
    }: {
      experimentId: string;
      payload: UpdateExperiment;
    }) => experimentsService.update(experimentId, payload),
    onSuccess: (_, v) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(v.experimentId)] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)] });
    },
  });

  const deleteSnapshotMutation = useMutation({
    mutationFn: experimentSnapshotsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.EXPERIMENTS.SNAPSHOTS(experimentIdsOrdered)],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.COMPARE.SNAPSHOT_FILES(experimentIdsOrdered)],
      });
    },
  });

  const displayedProjectMetrics = useMemo(() => {
    if (!project) return [];
    return getDisplayedTrackedMetrics(
      project.metrics.trackedMetrics,
      project.metrics.displayMetrics
    );
  }, [project]);

  const trackedMetricDefinitions = project?.metrics.trackedMetrics ?? [];

  const [featuresModalOpen, setFeaturesModalOpen] = useState(false);
  const [featureDiffsEnabled, setFeatureDiffsEnabled] = useState(true);

  const setActiveTab = (tab: DetailsTab) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "overview") {
      params.delete("detailsTab");
    } else {
      params.set("detailsTab", tab);
    }
    const q = params.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  };

  const handleSaveExperiment = async (experimentId: string, data: ExperimentEditSavePayload) => {
    await updateExperimentMutation.mutateAsync({
      experimentId,
      payload: {
        name: data.name,
        description: data.description,
        color: data.color,
        ...(data.parentExperimentId !== undefined
          ? { parentExperimentId: data.parentExperimentId }
          : {}),
      },
    });
    toast({ title: "Experiment updated" });
  };

  const handleStatusChange = async (experimentId: string, status: Experiment["status"]) => {
    await updateExperimentMutation.mutateAsync({ experimentId, payload: { status } });
    toast({ title: "Status updated" });
  };

  const handleTagsChange = async (experimentId: string, tags: string[]) => {
    await updateExperimentMutation.mutateAsync({ experimentId, payload: { tags } });
    toast({ title: "Tags updated" });
  };

  const handleDeleteSnapshot = async (experimentId: string) => {
    try {
      await deleteSnapshotMutation.mutateAsync(experimentId);
      toast({ title: "Snapshot deleted" });
    } catch {
      toast({ title: "Failed to delete snapshot", variant: "destructive" });
    }
  };

  if (experimentIdsOrdered.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader title="Experiment details" description="No experiments selected." />
        <p className="text-sm text-muted-foreground">
          Open this page from the experiments list via &quot;Details&quot; or add a valid{" "}
          <code className="text-xs">exp</code> query parameter.
        </p>
        <Button asChild variant="outline">
          <Link href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENTS(projectId)}>Back to experiments</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      <PageHeader
        title="Experiment details"
        description={
          project ? `${project.name} — ${experimentsOrdered.length} experiment(s)` : undefined
        }
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENTS(projectId)}>
              Back to experiments
            </Link>
          </Button>
        }
      />

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as DetailsTab)}
        className="space-y-6"
      >
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="overview" data-testid="tab-details-overview">
            Overview
          </TabsTrigger>
          <TabsTrigger value="metrics" data-testid="tab-details-metrics">
            Metrics
          </TabsTrigger>
          <TabsTrigger value="artifacts" data-testid="tab-details-artifacts">
            Artifacts
          </TabsTrigger>
          <TabsTrigger value="hparams" data-testid="tab-details-hparams">
            Hparams
          </TabsTrigger>
          <TabsTrigger value="features" data-testid="tab-details-features">
            Features
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-8 mt-0">
          {experimentsOrdered.map((experiment) => (
            <ExperimentDetailsMetadataCard
              key={experiment.id}
              experiment={experiment}
              project={project}
              projectExperiments={projectExperiments}
              onSave={(data) => handleSaveExperiment(experiment.id, data)}
              onStatusChange={(s) => handleStatusChange(experiment.id, s)}
              onTagsChange={(tags) => handleTagsChange(experiment.id, tags)}
              isSaving={updateExperimentMutation.isPending}
              snapshot={snapshotsByExperiment.get(experiment.id) ?? null}
              isSnapshotLoading={snapshotsQuery.isLoading}
              isDeletingSnapshot={
                deleteSnapshotMutation.isPending &&
                deleteSnapshotMutation.variables === experiment.id
              }
              onDeleteSnapshot={() => handleDeleteSnapshot(experiment.id)}
            />
          ))}

          {primaryExperimentId ? (
            <ExperimentDangerZoneCard
              experimentId={primaryExperimentId}
              projectId={projectId}
            />
          ) : null}
        </TabsContent>

        <TabsContent value="metrics" className="space-y-8 mt-0">
          {metricsTabActive ? (
            <>
              <Card>
            <CardHeader>
              <CardTitle>Selected metrics</CardTitle>
              <p className="text-sm text-muted-foreground">
                Values aggregated per project metric configuration (same as experiments table). When
                an experiment has a parent, the change vs parent is shown like on the DAG.
              </p>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Metric</TableHead>
                    {experimentsOrdered.map((e) => (
                      <TableHead key={e.id}>{e.name}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedProjectMetrics.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={1 + experimentsOrdered.length}
                        className="text-muted-foreground"
                      >
                        No display metrics configured for this project.
                      </TableCell>
                    </TableRow>
                  ) : (
                    displayedProjectMetrics.map((pm) => {
                      const direction = pm.direction === "minimize" ? "minimize" : "maximize";
                      const rowGroupHasDiff = experimentsOrdered.some((exp) => {
                        const parentId = exp.parentExperimentId;
                        if (parentId == null) return false;
                        const cellValue = aggregatedMetricsByExperiment[exp.id]?.find((m) =>
                          displayMetricKeyEquals(
                            { name: m.name, label: m.label },
                            { name: pm.name, label: pm.label ?? null }
                          )
                        )?.value;
                        const parentValue = aggregatedMetricsByExperiment[parentId]?.find((m) =>
                          displayMetricKeyEquals(
                            { name: m.name, label: m.label },
                            { name: pm.name, label: pm.label ?? null }
                          )
                        )?.value;
                        return cellValue != null && parentValue != null;
                      });
                      const metricTitle = formatMetricLabel(pm.name, pm.label ?? null);
                      return (
                        <TableRow key={projectMetricKeyString(pm)}>
                          <TableCell className="font-medium max-w-[14rem]">
                            <span
                              title={metricTitle}
                              className="block min-w-0 cursor-default truncate"
                            >
                              {metricTitle}
                            </span>
                          </TableCell>
                          {experimentsOrdered.map((e) => {
                            const value = aggregatedMetricsByExperiment[e.id]?.find((m) =>
                              displayMetricKeyEquals(
                                { name: m.name, label: m.label },
                                { name: pm.name, label: pm.label ?? null }
                              )
                            )?.value;
                            const parentId = e.parentExperimentId;
                            const parentValue =
                              parentId != null
                                ? aggregatedMetricsByExperiment[parentId]?.find((m) =>
                                    displayMetricKeyEquals(
                                      { name: m.name, label: m.label },
                                      { name: pm.name, label: pm.label ?? null }
                                    )
                                  )?.value
                                : undefined;
                            return (
                              <TableCell key={e.id} className="font-mono text-sm">
                                <MetricNameValueDiffRow
                                  metricName={pm.name}
                                  metricLabel={pm.label ?? null}
                                  value={value ?? null}
                                  parentValue={parentValue ?? null}
                                  direction={direction}
                                  showName={false}
                                  metricTable={{
                                    scope: "cell",
                                    groupHasAnyDiff: rowGroupHasDiff,
                                  }}
                                  classNameProps={{
                                    valueText: "text-sm",
                                    deltaText: "font-mono text-xs tabular-nums leading-none",
                                    deltaIcon: "w-2.5 h-2.5",
                                  }}
                                />
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {experimentsOrdered.map((experiment, idx) => (
            <ExperimentDetailsLoggedMetricsBlock
              key={experiment.id}
              experiment={experiment}
              projectId={projectId}
              metrics={metricsQueries[idx]?.data}
              metricsLoading={metricsQueries[idx]?.isLoading ?? false}
              trackedMetricDefinitions={trackedMetricDefinitions}
            />
          ))}
            </>
          ) : null}
        </TabsContent>

        <TabsContent value="artifacts" className="mt-0">
          {artifactsTabActive && primaryExperimentId ? (
            <ExperimentArtifactsPanel experimentId={primaryExperimentId} />
          ) : null}
        </TabsContent>

        <TabsContent value="hparams" className="mt-0">
          {activeTab === "hparams" && primaryExperimentId ? (
            <ExperimentHparamsPanel
              experimentId={primaryExperimentId}
              parentExperimentId={primaryExperiment?.parentExperimentId}
              enabled
            />
          ) : null}
        </TabsContent>

        <TabsContent value="features" className="mt-0">
          {featuresTabActive && primaryExperiment ? (
            <ExperimentFeaturesPanel
              experiment={primaryExperiment}
              parentExperiment={savedParentExperiment}
              projectExperiments={projectExperiments}
              modalOpen={featuresModalOpen}
              onModalOpenChange={setFeaturesModalOpen}
              lockExperimentFeaturesSelection
              showDiffs={featureDiffsEnabled}
              onShowDiffsChange={setFeatureDiffsEnabled}
            />
          ) : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ExperimentDetailsLoggedMetricsBlock({
  experiment,
  projectId,
  metrics,
  metricsLoading,
  trackedMetricDefinitions,
}: {
  experiment: Experiment;
  projectId: string;
  metrics: Metric[] | undefined;
  metricsLoading: boolean;
  trackedMetricDefinitions: ProjectMetric[];
}) {
  const { metrics: parentLoggedMetrics } = useExperimentMetrics(
    experiment.parentExperimentId ?? ""
  );

  return (
    <Card data-testid={`logged-metrics-${experiment.id}`}>
      <CardHeader className="py-3">
        <CardTitle className="text-base">Logged metrics — {experiment.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <ExperimentSidebarLoggedMetrics
          experimentId={experiment.id}
          projectId={projectId}
          metrics={metrics}
          metricsLoading={metricsLoading}
          parentLoggedMetrics={parentLoggedMetrics}
          trackedMetricDefinitions={trackedMetricDefinitions}
        />
      </CardContent>
    </Card>
  );
}

function ExperimentDetailsMetadataCard({
  experiment,
  project,
  projectExperiments,
  onSave,
  onStatusChange,
  onTagsChange,
  isSaving,
  snapshot,
  isSnapshotLoading,
  isDeletingSnapshot,
  onDeleteSnapshot,
}: {
  experiment: Experiment;
  project: Project | null | undefined;
  projectExperiments: Experiment[];
  onSave: (data: ExperimentEditSavePayload) => void;
  onStatusChange: (status: Experiment["status"]) => void;
  onTagsChange: (tags: string[]) => void;
  isSaving: boolean;
  snapshot: ExperimentSnapshot | null;
  isSnapshotLoading: boolean;
  isDeletingSnapshot: boolean;
  onDeleteSnapshot: () => Promise<void>;
}) {
  const [parentMenuOpen, setParentMenuOpen] = useState(false);
  const [deleteSnapshotOpen, setDeleteSnapshotOpen] = useState(false);
  const [parentFilter, setParentFilter] = useState("");
  const parentFilterInputRef = useRef<HTMLInputElement>(null);
  const [draftParentExperimentId, setDraftParentExperimentId] = useState<string | null>(
    experiment.parentExperimentId ?? null
  );

  /* eslint-disable react-hooks/set-state-in-effect -- draft parent matches server after refetch */
  useEffect(() => {
    setDraftParentExperimentId(experiment.parentExperimentId ?? null);
  }, [experiment.id, experiment.parentExperimentId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!parentMenuOpen) {
      return;
    }
    requestAnimationFrame(() => parentFilterInputRef.current?.focus());
  }, [parentMenuOpen]);

  const parentCandidates = useMemo(() => {
    return projectExperiments.filter((e) => e.id !== experiment.id);
  }, [projectExperiments, experiment.id]);

  const filteredParentCandidates = useMemo(() => {
    const q = parentFilter.trim();
    if (!q) return parentCandidates;
    return parentCandidates.filter((e) => experimentMatchesSearch(e, q));
  }, [parentCandidates, parentFilter]);

  return (
    <Card data-testid={`experiment-details-metadata-${experiment.id}`}>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: experiment.color || "#3b82f6" }}
            />
            <CardTitle className="text-lg">{experiment.name}</CardTitle>
            <StatusBadge status={experiment.status} />
            {project ? <Badge variant="secondary">{project.name}</Badge> : null}
            <ExperimentTagsEditor
              tags={experiment.tags ?? []}
              disabled={isSaving}
              onChange={onTagsChange}
            />
          </div>
          <EntityIdDisplay label="ID" value={experiment.id} />
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2 border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
            disabled={isSnapshotLoading || !snapshot?.snapshotId || isDeletingSnapshot}
            onClick={() => setDeleteSnapshotOpen(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            {isDeletingSnapshot ? "Deleting..." : "Delete Snapshot"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Parent experiment</p>
          <div className="flex w-full items-stretch gap-1 max-w-xl">
            <DropdownMenu
              open={parentMenuOpen}
              onOpenChange={(open) => {
                setParentMenuOpen(open);
                if (!open) setParentFilter("");
              }}
            >
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  disabled={isSaving}
                  className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-left text-sm shadow-sm"
                >
                  <GitBranch className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate">
                    {draftParentExperimentId ? (
                      formatExperimentParentOption(
                        projectExperiments.find((e) => e.id === draftParentExperimentId) ?? {
                          name: draftParentExperimentId.slice(0, 8),
                          id: draftParentExperimentId,
                        }
                      )
                    ) : (
                      <span className="text-muted-foreground">No parent</span>
                    )}
                  </span>
                  <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="max-h-80 overflow-y-auto w-[min(28rem,calc(100vw-2rem))]">
                <div className="p-2 border-b">
                  <Input
                    ref={parentFilterInputRef}
                    placeholder="Filter by id, name, description, tags…"
                    value={parentFilter}
                    onChange={(e) => setParentFilter(e.target.value)}
                  />
                </div>
                {filteredParentCandidates.length === 0 ? (
                  <div className="p-2 text-sm text-muted-foreground">No matches</div>
                ) : (
                  filteredParentCandidates.map((exp) => (
                    <DropdownMenuItem
                      key={exp.id}
                      onSelect={() => {
                        setDraftParentExperimentId(exp.id);
                        setParentMenuOpen(false);
                      }}
                    >
                      {formatExperimentParentOption(exp)}
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            {draftParentExperimentId ? (
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 shrink-0"
                onClick={() => setDraftParentExperimentId(null)}
                aria-label="Clear parent"
              >
                <X className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
        </div>

        <ExperimentEditForm
          experiment={experiment}
          onSave={onSave}
          isSaving={isSaving}
          draftParentExperimentId={draftParentExperimentId}
          savedParentExperimentId={experiment.parentExperimentId ?? null}
        />

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Select value={experiment.status} onValueChange={(v) => onStatusChange(v as Experiment["status"])}>
            <SelectTrigger className="w-36 h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="planned">Planned</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="complete">Complete</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm max-w-md">
          <div className="p-2 rounded-md bg-muted/50">
            <p className="text-muted-foreground text-xs">Created</p>
            <p className="font-medium">
              {format(parseISO(experiment.createdAt), "MMM d, yyyy, HH:mm")}
            </p>
          </div>
          <div className="p-2 rounded-md bg-muted/50">
            <p className="text-muted-foreground text-xs">Started</p>
            <p className="font-medium">
              {experiment.startedAt
                ? format(parseISO(experiment.startedAt), "MMM d, yyyy, HH:mm")
                : "-"}
            </p>
          </div>
        </div>
      </CardContent>
      <Dialog open={deleteSnapshotOpen} onOpenChange={setDeleteSnapshotOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete snapshot?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This removes the file snapshot for {experiment.name}. Project artifacts used by other
            snapshots are kept when still referenced.
          </p>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteSnapshotOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeletingSnapshot}
              onClick={() => {
                void onDeleteSnapshot().then(() => setDeleteSnapshotOpen(false));
              }}
            >
              Delete Snapshot
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
