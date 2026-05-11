"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import {
  ExperimentEditForm,
  type ExperimentEditSavePayload,
} from "@/components/shared/experiment-edit-form";
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
import { Label } from "@/components/ui/label";
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
import { ExperimentArtifactsPanel } from "@/domain/experiment-artifacts/components/experiment-artifacts-panel";
import { useAggregatedMetrics, useExperiments } from "@/domain/experiments/hooks";
import type { Experiment } from "@/domain/experiments/types";
import type { UpdateExperiment } from "@/domain/experiments/types/dto";
import type { Metric } from "@/domain/metrics/types";
import { metricsService } from "@/domain/metrics/services/metrics-service";
import { useProject } from "@/domain/projects/hooks/project-hook";
import type { Project } from "@/domain/projects/types";
import { ScalarsMetricsGrid } from "@/domain/scalars/components/scalars-metrics-grid";
import { useMetricDomains } from "@/domain/scalars/hooks/use-metric-domains";
import { useProjectScalars } from "@/domain/scalars/hooks/project-scalars-hook";
import { useScalarsDataModel } from "@/domain/scalars/hooks/use-scalars-data-model";
import { decodeStringSelection } from "@/domain/scalars/utils/selection-codec";
import type { SyncMode } from "@/domain/scalars/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import {
  displayMetricKeyEquals,
  formatMetricLabel,
  getDisplayedTrackedMetrics,
  projectMetricKeyString,
} from "@/lib/metrics/format-metric-label";
import {
  formatMetricScalarForDisplay,
  formatMetricScalarForEditorDraft,
  formatMetricScalarForEditorFull,
  metricEditorValuesEffectivelyEqual,
} from "@/lib/metrics/metric-value-display";
import { MetricDeltaVsParent } from "@/components/shared/metric-delta-vs-parent";
import { useToast } from "@/lib/hooks/use-toast";
import { GitBranch, ChevronDown, X } from "lucide-react";
import { format, parseISO } from "date-fns";
import { experimentsService } from "@/domain/experiments/services";
import { ExperimentDangerZoneCard } from "@/domain/experiments/components/experiment-danger-zone-card";
import type { InsertExperiment } from "@/domain/experiments/types";
function formatExperimentParentOption(exp: Pick<Experiment, "name" | "id">): string {
  return `${exp.name} (${exp.id.slice(0, 7)})`;
}

/**
 * Strict parse for logged metric value fields. `Number.parseFloat` only reads a prefix and drops
 * trailing garbage (`parseFloat("1.2x") === 1.2`); `Number(trimmed)` requires the whole string to
 * be a numeric literal, so typos at the end are rejected instead of truncated.
 */
function parseLoggedMetricValueInput(trimmed: string): number | null {
  if (trimmed === "") return null;
  const num = Number(trimmed);
  if (!Number.isFinite(num)) return null;
  return num;
}

export function ExperimentDetailsView({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const experimentIdsOrdered = useMemo(
    () => decodeStringSelection(searchParams.get("exp")),
    [searchParams]
  );

  const { experiments: projectExperiments } = useExperiments(projectId);
  const { project } = useProject(projectId);
  const { aggregatedMetricsByExperiment } = useAggregatedMetrics(projectId);

  const experimentsOrdered = useMemo(() => {
    const map = new Map(projectExperiments.map((e) => [e.id, e]));
    return experimentIdsOrdered.map((id) => map.get(id)).filter((e): e is Experiment => !!e);
  }, [projectExperiments, experimentIdsOrdered]);

  const primaryExperimentId = experimentIdsOrdered[0] ?? "";

  const metricsQueries = useQueries({
    queries: experimentIdsOrdered.map((experimentId) => ({
      queryKey: [QUERY_KEYS.METRICS.GET(experimentId)],
      queryFn: () => metricsService.getByExperiment(experimentId),
      enabled: experimentIdsOrdered.length > 0,
    })),
  });

  const updateExperimentMutation = useMutation({
    mutationFn: async ({
      experimentId,
      payload,
    }: {
      experimentId: string;
      payload: UpdateExperiment;
    }) => experimentsService.update(experimentId, payload as InsertExperiment),
    onSuccess: (_, v) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_ID(v.experimentId)] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)] });
    },
  });

  const upsertMetricMutation = useMutation({
    mutationFn: metricsService.upsert,
    onSuccess: (_, v) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.GET(v.experimentId)] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.BY_PROJECT(projectId)] });
    },
  });

  const deleteMetricMutation = useMutation({
    mutationFn: metricsService.delete,
    onSuccess: () => {
      for (const id of experimentIdsOrdered) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.GET(id)] });
      }
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.METRICS.BY_PROJECT(projectId)] });
    },
  });

  const displayedProjectMetrics = useMemo(() => {
    if (!project) return [];
    return getDisplayedTrackedMetrics(
      project.metrics.trackedMetrics,
      project.metrics.displayMetrics
    );
  }, [project]);

  const selectedExperimentIds = useMemo(
    () => new Set(experimentIdsOrdered),
    [experimentIdsOrdered]
  );

  const [hiddenMetrics, setHiddenMetrics] = useState<Set<string>>(new Set());
  const [smoothing, setSmoothing] = useState(0);
  const cardHeight = 220;
  const cardMinWidth = 320;

  const {
    scalars,
    isLoading: scalarsLoading,
    refetch: refetchScalars,
  } = useProjectScalars({
    projectId,
    experimentIds: experimentIdsOrdered.length ? experimentIdsOrdered : undefined,
    returnTags: false,
  });

  const {
    visibleMetrics,
    visibleExperiments,
    chartDataByMetric,
    allLoggedMetricNames,
  } = useScalarsDataModel({
    experiments: projectExperiments,
    scalars,
    selectedExperimentIds,
    hiddenMetrics,
    smoothing,
    soloMode: false,
    chosenExperimentId: null,
    experimentDisplayOrder: experimentIdsOrdered,
  });

  const syncMode: SyncMode = "all";
  const { metricDomains, handleDomainChange, resetDomain } = useMetricDomains(
    visibleMetrics.map((m) => m.name),
    syncMode
  );

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
    <div className="space-y-8 pb-16">
      <PageHeader
        title="Experiment details"
        description={
          project ? `${project.name} — ${experimentsOrdered.length} experiment(s)` : undefined
        }
        actions={
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENTS(projectId)}>
                Back to experiments
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => void refetchScalars()}>
              Refresh scalars
            </Button>
          </div>
        }
      />

      {experimentsOrdered.map((experiment) => (
        <ExperimentDetailsMetadataCard
          key={experiment.id}
          experiment={experiment}
          project={project}
          projectExperiments={projectExperiments}
          onSave={(data) => handleSaveExperiment(experiment.id, data)}
          onStatusChange={(s) => handleStatusChange(experiment.id, s)}
          isSaving={updateExperimentMutation.isPending}
        />
      ))}

      <Card>
        <CardHeader>
          <CardTitle>Selected metrics</CardTitle>
          <p className="text-sm text-muted-foreground">
            Values aggregated per project metric configuration (same as experiments table). When an
            experiment has a parent, the change vs parent is shown like on the DAG.
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
                  <TableCell colSpan={1 + experimentsOrdered.length} className="text-muted-foreground">
                    No display metrics configured for this project.
                  </TableCell>
                </TableRow>
              ) : (
                displayedProjectMetrics.map((pm) => (
                  <TableRow key={projectMetricKeyString(pm)}>
                    <TableCell className="font-medium">
                      {formatMetricLabel(pm.name, pm.label ?? null)}
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
                      const direction = pm.direction === "minimize" ? "minimize" : "maximize";
                      return (
                        <TableCell key={e.id} className="font-mono text-sm">
                          <div className="flex flex-wrap items-center gap-1 min-w-0">
                            <span>{formatMetricScalarForDisplay(value ?? null)}</span>
                            <MetricDeltaVsParent
                              value={value ?? null}
                              parentValue={parentValue ?? null}
                              direction={direction}
                              textClassName="font-mono text-xs tabular-nums leading-none"
                            />
                          </div>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {experimentIdsOrdered.map((expId, idx) => (
        <LoggedMetricsEditor
          key={expId}
          experimentId={expId}
          experimentName={experimentsOrdered[idx]?.name ?? expId}
          metrics={metricsQueries[idx]?.data ?? []}
          isLoading={metricsQueries[idx]?.isLoading ?? false}
          onUpsert={(body) => upsertMetricMutation.mutateAsync(body)}
          onDelete={(id) => deleteMetricMutation.mutateAsync(id)}
        />
      ))}

      <Card>
        <CardHeader>
          <CardTitle>Scalars</CardTitle>
          <p className="text-sm text-muted-foreground">
            Time-series metrics for the experiments in this view (URL order).
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4 text-sm items-center">
            <Label className="w-32">Smoothing</Label>
            <Input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={smoothing}
              onChange={(e) => setSmoothing(Number.parseFloat(e.target.value))}
              className="max-w-xs"
            />
            <span className="text-muted-foreground w-10">{smoothing.toFixed(2)}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setHiddenMetrics(new Set())}
            >
              Show all metrics
            </Button>
            {allLoggedMetricNames.map((name) => (
              <Button
                key={name}
                size="sm"
                variant={hiddenMetrics.has(name) ? "secondary" : "outline"}
                onClick={() =>
                  setHiddenMetrics((prev) => {
                    const next = new Set(prev);
                    if (next.has(name)) next.delete(name);
                    else next.add(name);
                    return next;
                  })
                }
              >
                {hiddenMetrics.has(name) ? `Show ${name}` : `Hide ${name}`}
              </Button>
            ))}
          </div>
          {scalarsLoading ? (
            <p className="text-sm text-muted-foreground">Loading scalars…</p>
          ) : (
            <ScalarsMetricsGrid
              visibleMetrics={visibleMetrics}
              chartDataByMetric={chartDataByMetric}
              metricDomains={metricDomains}
              cardHeight={cardHeight}
              cardMinWidth={cardMinWidth}
              allExperiments={projectExperiments}
              visibleExperiments={visibleExperiments}
              onResetDomain={resetDomain}
              onExpandMetric={() => {}}
              onHideMetric={(name) =>
                setHiddenMetrics((prev) => new Set(prev).add(name))
              }
              onDomainChange={handleDomainChange}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Experiment artifacts</CardTitle>
        </CardHeader>
        <CardContent>
          {primaryExperimentId ? (
            <ExperimentArtifactsPanel
              projectId={projectId}
              primaryExperimentId={primaryExperimentId}
              compareExperimentIds={experimentIdsOrdered}
              urlTabParam
            />
          ) : null}
        </CardContent>
      </Card>

      {primaryExperimentId ? (
        <ExperimentDangerZoneCard
          experimentId={primaryExperimentId}
          projectId={projectId}
        />
      ) : null}
    </div>
  );
}

function ExperimentDetailsMetadataCard({
  experiment,
  project,
  projectExperiments,
  onSave,
  onStatusChange,
  isSaving,
}: {
  experiment: Experiment;
  project: Project | null | undefined;
  projectExperiments: Experiment[];
  onSave: (data: ExperimentEditSavePayload) => void;
  onStatusChange: (status: Experiment["status"]) => void;
  isSaving: boolean;
}) {
  const [parentMenuOpen, setParentMenuOpen] = useState(false);
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
    const q = parentFilter.trim().toLowerCase();
    if (!q) return parentCandidates;
    return parentCandidates.filter((e) => {
      const label = formatExperimentParentOption(e).toLowerCase();
      return label.includes(q) || e.id.toLowerCase().includes(q);
    });
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
          </div>
          <p className="text-xs font-mono text-muted-foreground">{experiment.id}</p>
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
                    placeholder="Filter…"
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
    </Card>
  );
}

type AddMetricDialogMode = "new-label" | "group";

function LoggedMetricsEditor({
  experimentId,
  experimentName,
  metrics,
  isLoading,
  onUpsert,
  onDelete,
}: {
  experimentId: string;
  experimentName: string;
  metrics: Metric[];
  isLoading: boolean;
  onUpsert: (payload: {
    experimentId: string;
    name: string;
    value: number;
    label?: string | null;
  }) => Promise<Metric>;
  onDelete: (metricId: string) => Promise<void>;
}) {
  const { toast } = useToast();
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});
  const [addOpen, setAddOpen] = useState(false);
  const [addMode, setAddMode] = useState<AddMetricDialogMode>("group");
  /** Label for the group being added to; ignored when addMode === "new-label" (user enters label). */
  const [addGroupLabel, setAddGroupLabel] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newValue, setNewValue] = useState("0");

  const metricsByLabelGroups = useMemo(() => {
    if (!metrics.length) {
      return [] as { label: string | null; items: Metric[] }[];
    }
    const map = new Map<string, Metric[]>();
    for (const m of metrics) {
      const k = m.label ?? "";
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(m);
    }
    const entries = [...map.entries()];
    entries.sort((a, b) => {
      if (a[0] === "" && b[0] !== "") return 1;
      if (b[0] === "" && a[0] !== "") return -1;
      return a[0].localeCompare(b[0]);
    });
    for (const [, items] of entries) {
      items.sort((a, b) => a.name.localeCompare(b.name));
    }
    return entries.map(([k, items]) => ({
      label: k === "" ? null : k,
      items,
    }));
  }, [metrics]);

  /* eslint-disable react-hooks/set-state-in-effect -- reset drafts when metrics refetch */
  useEffect(() => {
    const nextVal: Record<string, string> = {};
    const nextName: Record<string, string> = {};
    for (const m of metrics) {
      nextVal[m.id] = formatMetricScalarForEditorDraft(m.value);
      nextName[m.id] = m.name;
    }
    setDraftValues(nextVal);
    setDraftNames(nextName);
  }, [metrics]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const openAddNewLabel = () => {
    setAddMode("new-label");
    setAddGroupLabel(null);
    setNewName("");
    setNewLabel("");
    setNewValue("0");
    setAddOpen(true);
  };

  const openAddToGroup = (groupLabel: string | null) => {
    setAddMode("group");
    setAddGroupLabel(groupLabel);
    setNewName("");
    setNewLabel(groupLabel ?? "");
    setNewValue("0");
    setAddOpen(true);
  };

  /** Persist value input on blur: skip HTTP if parse fails or value is unchanged (exact short draft, or bitwise same double as stored). */
  const flushValue = async (m: Metric) => {
    const raw = draftValues[m.id];
    if (raw === undefined) return;
    const trimmed = raw.trim();
    const num = parseLoggedMetricValueInput(trimmed);
    if (num === null) {
      toast({ title: "Value can't be parsed", variant: "destructive" });
      // Revert to the compact display string (not the in-progress invalid text).
      setDraftValues((prev) => ({ ...prev, [m.id]: formatMetricScalarForEditorDraft(m.value) }));
      return;
    }
    const short = formatMetricScalarForEditorDraft(m.value);
    if (trimmed === short || Object.is(num, m.value)) {
      setDraftValues((prev) => ({ ...prev, [m.id]: short }));
      return;
    }
    await onUpsert({
      experimentId,
      name: m.name,
      value: num,
      label: m.label,
    });
    toast({ title: "Metric updated" });
  };

  const flushName = async (m: Metric) => {
    const raw = draftNames[m.id];
    if (raw === undefined) return;
    const name = raw.trim();
    if (!name) {
      toast({ title: "Name required", variant: "destructive" });
      setDraftNames((prev) => ({ ...prev, [m.id]: m.name }));
      return;
    }
    if (name === m.name) return;
    await onDelete(m.id);
    await onUpsert({
      experimentId,
      name,
      value: m.value,
      label: m.label,
    });
    toast({ title: "Metric updated" });
  };

  const handleAdd = async () => {
    if (!newName.trim()) {
      toast({ title: "Name is required", variant: "destructive" });
      return;
    }
    const num = parseLoggedMetricValueInput(newValue.trim());
    if (num === null) {
      toast({ title: "Value can't be parsed", variant: "destructive" });
      return;
    }
    let label: string | null;
    if (addMode === "new-label") {
      const trimmed = newLabel.trim();
      if (!trimmed) {
        toast({ title: "Label is required", variant: "destructive" });
        return;
      }
      label = trimmed;
    } else {
      label = addGroupLabel;
    }
    await onUpsert({
      experimentId,
      name: newName.trim(),
      value: num,
      label,
    });
    toast({ title: "Metric added" });
    setAddOpen(false);
    setNewName("");
    setNewLabel("");
    setNewValue("0");
  };

  /** Metric name field: chrome matches value (no heavy border until hover/focus). */
  const nameInputClass =
    "h-8 min-w-[8rem] max-w-[20rem] font-medium border-transparent bg-transparent px-2 shadow-none hover:border-input focus-visible:border-input focus-visible:ring-1";

  /** Wider monospace value field; same border treatment as name. */
  const valueInputClass =
    "h-8 min-w-[12rem] max-w-[24rem] w-full font-mono border-transparent bg-transparent px-2 shadow-none hover:border-input focus-visible:border-input focus-visible:ring-1";

  return (
    <Card data-testid={`logged-metrics-${experimentId}`}>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle className="text-base">Logged metrics — {experimentName}</CardTitle>
        <Button size="sm" variant="outline" onClick={openAddNewLabel} data-testid="button-add-metric-label">
          Add label
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : metricsByLabelGroups.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">No logged metrics yet.</p>
            <Button size="sm" variant="secondary" onClick={() => openAddToGroup(null)}>
              Add unlabeled metric
            </Button>
          </div>
        ) : (
          metricsByLabelGroups.map((group) => (
            <div key={group.label ?? "__unlabeled"} className="space-y-2" data-testid={`metric-group-${group.label ?? "unlabeled"}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-muted-foreground">
                  {group.label != null ? (
                    <>
                      Label: <span className="text-foreground">{group.label}</span>
                    </>
                  ) : (
                    "Unlabeled"
                  )}
                </p>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 text-xs"
                  onClick={() => openAddToGroup(group.label)}
                  data-testid={`button-add-metric-group-${group.label ?? "unlabeled"}`}
                >
                  Add metric
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="min-w-[12rem] w-[14rem]">Value</TableHead>
                    <TableHead className="w-12 text-right p-0" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.items.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell className="py-1.5">
                        {/* Inline edit; blur persists via flushName (recreates row if name changed). */}
                        <Input
                          className={nameInputClass}
                          value={draftNames[m.id] ?? m.name}
                          onChange={(e) =>
                            setDraftNames((prev) => ({ ...prev, [m.id]: e.target.value }))
                          }
                          onBlur={() => void flushName(m)}
                          aria-label="Metric name"
                          data-testid={`metric-name-${m.id}`}
                        />
                      </TableCell>
                      <TableCell className="py-1.5">
                        {/*
                          Blurred: short draft. On focus, swap to full plain-decimal text when the field
                          still matches the server value: either it is exactly the short draft, or the
                          parsed number matches `m.value` (see metricEditorValuesEffectivelyEqual). The
                          short string alone can parse slightly off the stored double, so we must not
                          rely only on numeric equality for the pristine short case.
                          Unparseable text: no toast here — only flushValue (onBlur) shows errors / success.
                          Parsing uses strict full-string `Number(...)` (not parseFloat) so trailing typos
                          are not silently dropped from the right-hand side of the field.
                        */}
                        <Input
                          className={valueInputClass}
                          value={draftValues[m.id] ?? formatMetricScalarForEditorDraft(m.value)}
                          onChange={(e) =>
                            setDraftValues((prev) => ({ ...prev, [m.id]: e.target.value }))
                          }
                          onFocus={() =>
                            setDraftValues((prev) => {
                              const short = formatMetricScalarForEditorDraft(m.value);
                              const full = formatMetricScalarForEditorFull(m.value);
                              const cur = prev[m.id] ?? short;
                              const parsed = parseLoggedMetricValueInput(cur.trim());
                              if (parsed === null) return prev;
                              const stillServerValue =
                                cur === short ||
                                metricEditorValuesEffectivelyEqual(parsed, m.value);
                              if (!stillServerValue) return prev;
                              if (cur === full) return prev;
                              return { ...prev, [m.id]: full };
                            })
                          }
                          onBlur={() => void flushValue(m)}
                          data-testid={`metric-value-${m.id}`}
                        />
                      </TableCell>
                      <TableCell className="py-1.5 text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          aria-label="Remove metric"
                          onClick={() =>
                            void onDelete(m.id).then(() => toast({ title: "Metric removed" }))
                          }
                          data-testid={`metric-remove-${m.id}`}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ))
        )}

        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {addMode === "new-label" ? "Add label & metric" : "Add metric"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              {addMode === "new-label" ? (
                <div className="space-y-1">
                  <Label>New label</Label>
                  <Input
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    placeholder="e.g. fold_1"
                    autoFocus
                  />
                </div>
              ) : (
                <div className="rounded-md bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
                  {addGroupLabel != null ? (
                    <>
                      Adding under label: <span className="font-medium text-foreground">{addGroupLabel}</span>
                    </>
                  ) : (
                    "Adding unlabeled metric"
                  )}
                </div>
              )}
              <div className="space-y-1">
                <Label>Name</Label>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Value</Label>
                <Input value={newValue} onChange={(e) => setNewValue(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => void handleAdd()}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
