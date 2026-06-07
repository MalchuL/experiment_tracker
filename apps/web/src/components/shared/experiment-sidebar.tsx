"use client";

/**
 * Slide-over panel for a single experiment: edit core fields, pick a parent, view tracked vs parent
 * metrics, browse logged scalars by label, and inspect features / git diff.
 */

import Link from "next/link";
import { StatusBadge } from "@/components/shared/status-badge";
import { EntityIdDisplay } from "@/components/shared/entity-id-display";
import {
  ExperimentEditForm,
  type ExperimentEditSavePayload,
} from "@/components/shared/experiment-edit-form";
import { ExperimentTagsEditor } from "@/domain/experiments/components/experiment-tags-editor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RightSidebarShell, type RightSidebarVariant } from "@/components/shared/right-sidebar-shell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { useToast } from "@/lib/hooks/use-toast";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useExperiment } from "@/domain/experiments/hooks/experiment-hook";
import { useExperiments } from "@/domain/experiments/hooks/experiments-hook";
import { Download, FileCode2, GitBranch, GitCompare, Loader2, RefreshCw, X, ChevronDown } from "lucide-react";
import { format, parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type { Metric } from "@/domain/metrics/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { useExperimentMetrics } from "@/domain/metrics/hooks";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { REFRESH_EXPERIMENT_SIDEBAR_INTERVAL } from "@/lib/constants/rates";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { cn } from "@/lib/utils";
import { displayMetricKeyEquals, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import {
  MetricNameValueDiffRow,
  metricRowGroupTableClass,
} from "@/components/shared/metric-name-value-diff-row";
import { ExperimentFeaturesPanel } from "@/components/shared/experiment-features-panel";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ExperimentHparamsPanel } from "@/components/shared/experiment-hparams-panel";
import { experimentSnapshotsService } from "@/domain/experiments/services";
import { downloadBlob, sanitizeDownloadName } from "@/lib/downloads";

/** One bucket of logged scalars sharing the same label (or “unlabeled”). */
type LoggedMetricsLabelGroup = { label: string | null; items: Metric[] };
type ExperimentSidebarTab = "metrics" | "features" | "hparams" | "code";

const EXPERIMENT_SIDEBAR_ACTIVE_TAB_STORAGE_KEY = "experiment-sidebar.active-tab";
const EXPERIMENT_SIDEBAR_FEATURE_DIFFS_STORAGE_KEY = "experiment-sidebar.feature-diffs";
const EXPERIMENT_SIDEBAR_TABS: ExperimentSidebarTab[] = ["metrics", "features", "hparams", "code"];
const EXPERIMENT_SIDEBAR_MIN_WIDTH = 320;
const EXPERIMENT_SIDEBAR_MAX_WIDTH = 760;
const EXPERIMENT_SIDEBAR_DEFAULT_WIDTH = 400;
const METRIC_SIDEBAR_ROW_SEPARATOR_CLASS = "border-b border-border/35 py-1";
const METRIC_SIDEBAR_DENSE_CLASS_NAMES = {
  root: "text-sm",
  nameCluster: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  valueCluster: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableSlot1: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableArrow: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  tableSlot2: METRIC_SIDEBAR_ROW_SEPARATOR_CLASS,
  deltaText: "font-mono text-xs tabular-nums leading-none",
  deltaIcon: "w-2.5 h-2.5",
};
const METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES = {
  ...METRIC_SIDEBAR_DENSE_CLASS_NAMES,
  root: "text-sm pl-0",
};

/**
 * Looks up the numeric value for a project “tracked” metric inside an experiment’s aggregated
 * metric list (same name + label as the project definition).
 */
function lookupAggregatedValueForTrackedMetric(
  aggregatedMetrics: Metric[] | undefined,
  trackedMetric: ProjectMetric
): number | null | undefined {
  const matchedRow = aggregatedMetrics?.find((row) =>
    displayMetricKeyEquals(
      { name: row.name, label: row.label },
      { name: trackedMetric.name, label: trackedMetric.label ?? null }
    )
  );
  return matchedRow?.value;
}

/**
 * Finds the project tracked-metric definition that matches a logged scalar row, if the project
 * tracks that name/label (used to know direction and whether we can compare to the parent).
 */
function findTrackedDefinitionForLoggedMetric(
  trackedDefinitions: ProjectMetric[],
  loggedMetric: Pick<Metric, "name" | "label">
): ProjectMetric | undefined {
  return trackedDefinitions.find((tracked) =>
    displayMetricKeyEquals(
      { name: loggedMetric.name, label: loggedMetric.label },
      { name: tracked.name, label: tracked.label ?? null }
    )
  );
}

/**
 * Stable `Accordion` item value for a label bucket. Null/empty labels map to a sentinel so default
 * open state does not collide with a real empty-string label.
 */
function accordionItemValueForLoggedLabelGroup(label: string | null): string {
  if (label == null || label === "") return "__unlabeled__";
  return label;
}

/** Single-line label for parent dropdown rows (name + short id prefix). */
function formatExperimentParentOption(exp: Pick<Experiment, "name" | "id">): string {
  return `${exp.name} (${exp.id.slice(0, 7)})`;
}

function buildCodeCompareHref(experiment: Pick<Experiment, "id" | "projectId" | "parentExperimentId">): string {
  const params = new URLSearchParams();
  if (experiment.parentExperimentId) {
    params.append("exp", experiment.parentExperimentId);
    params.append("exp", experiment.id);
  } else {
    params.append("exp", experiment.id);
  }
  return `${FRONTEND_ROUTES.PROJECT_PAGES.COMPARE(experiment.projectId)}?${params.toString()}`;
}

function buildCodeFilesHref(experiment: Pick<Experiment, "id" | "projectId">): string {
  const params = new URLSearchParams();
  params.append("exp", experiment.id);
  return `${FRONTEND_ROUTES.PROJECT_PAGES.COMPARE(experiment.projectId)}?${params.toString()}`;
}

function readStoredSidebarTab(): ExperimentSidebarTab {
  if (typeof window === "undefined") return "metrics";
  const storedValue = window.localStorage.getItem(EXPERIMENT_SIDEBAR_ACTIVE_TAB_STORAGE_KEY);
  return EXPERIMENT_SIDEBAR_TABS.includes(storedValue as ExperimentSidebarTab)
    ? (storedValue as ExperimentSidebarTab)
    : "metrics";
}

function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const storedValue = window.localStorage.getItem(key);
  if (storedValue === "1") return true;
  if (storedValue === "0") return false;
  return fallback;
}

function writeLocalStorageValue(key: string, value: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, value);
}

interface ExperimentSidebarProps {
  experimentId: string | null;
  onClose: () => void;
  projectMetrics?: ProjectMetric[];
  /** Per-experiment aggregated display metrics; used for values and parent deltas. */
  aggregatedMetricsByExperiment?: Record<string, Metric[]>;
  /** `push` = list/kanban (main area shrinks); `overlay` = graph/full-bleed (default). */
  variant?: RightSidebarVariant;
}

export function ExperimentSidebar({
  experimentId,
  onClose,
  projectMetrics,
  aggregatedMetricsByExperiment,
  variant = "overlay",
}: ExperimentSidebarProps) {
  const { toast } = useToast();

  // Parent picker: dropdown filter + draft selection (committed from the edit form on save).
  const [parentMenuOpen, setParentMenuOpen] = useState(false);
  const [parentSearchQuery, setParentSearchQuery] = useState("");
  const parentSearchInputRef = useRef<HTMLInputElement>(null);
  const [draftParentExperimentId, setDraftParentExperimentId] = useState<string | null>(null);
  const [featuresModalOpen, setFeaturesModalOpen] = useState(false);
  const [downloadSnapshotOpen, setDownloadSnapshotOpen] = useState(false);
  const [snapshotDownloadPending, setSnapshotDownloadPending] = useState(false);
  const [activeTab, setActiveTab] = useState<ExperimentSidebarTab>(() => readStoredSidebarTab());
  const [featureDiffsEnabled, setFeatureDiffsEnabled] = useState<boolean>(() =>
    readStoredBoolean(EXPERIMENT_SIDEBAR_FEATURE_DIFFS_STORAGE_KEY, true)
  );
  const [sidebarWidth, setSidebarWidth] = useState(EXPERIMENT_SIDEBAR_DEFAULT_WIDTH);

  useEffect(() => {
    if (!parentMenuOpen) {
      setParentSearchQuery("");
      return;
    }
    requestAnimationFrame(() => parentSearchInputRef.current?.focus());
  }, [parentMenuOpen]);

  useEffect(() => {
    writeLocalStorageValue(EXPERIMENT_SIDEBAR_ACTIVE_TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

  useEffect(() => {
    writeLocalStorageValue(
      EXPERIMENT_SIDEBAR_FEATURE_DIFFS_STORAGE_KEY,
      featureDiffsEnabled ? "1" : "0"
    );
  }, [featureDiffsEnabled]);

  const handleSidebarResizeStart = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = sidebarWidth;

      const handlePointerMove = (moveEvent: PointerEvent) => {
        const viewportMax = Math.max(
          EXPERIMENT_SIDEBAR_MIN_WIDTH,
          window.innerWidth - 240
        );
        const maxWidth = Math.min(EXPERIMENT_SIDEBAR_MAX_WIDTH, viewportMax);
        setSidebarWidth(
          Math.min(
            maxWidth,
            Math.max(EXPERIMENT_SIDEBAR_MIN_WIDTH, startWidth + startX - moveEvent.clientX)
          )
        );
      };

      const handlePointerUp = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [sidebarWidth]
  );

  // Primary record + mutations for the sidebar experiment (light polling while mounted).
  const {
    experiment,
    isLoading: experimentLoading,
    isFetching: experimentFetching,
    updateIsPending,
    updateExperiment,
    refetch,
  } = useExperiment(experimentId || "", { refetchInterval: REFRESH_EXPERIMENT_SIDEBAR_INTERVAL });

  const { metrics, isLoading: metricsLoading } = useExperimentMetrics(experimentId || "");
  const { metrics: parentLoggedMetrics } = useExperimentMetrics(experiment?.parentExperimentId ?? "");
  const {
    experiment: savedParentExperiment,
  } = useExperiment(experiment?.parentExperimentId ?? "");
  const { project } = useProject(experiment?.projectId);

  const trackedMetricDefinitions = project?.metrics.trackedMetrics ?? [];
  const experimentTags = experiment?.tags ?? [];

  /** Logged scalars grouped by label for accordion sections (locale-sorted labels; unlabeled last). */
  const loggedMetricsByLabel = useMemo((): LoggedMetricsLabelGroup[] => {
    if (!metrics?.length) {
      return [];
    }
    const metricsByLabelKey = new Map<string, Metric[]>();
    for (const loggedMetric of metrics) {
      const rawLabelKey = loggedMetric.label ?? "";
      if (!metricsByLabelKey.has(rawLabelKey)) metricsByLabelKey.set(rawLabelKey, []);
      metricsByLabelKey.get(rawLabelKey)!.push(loggedMetric);
    }
    const sortedLabelEntries = [...metricsByLabelKey.entries()];
    sortedLabelEntries.sort((a, b) => {
      if (a[0] === "" && b[0] !== "") return 1;
      if (b[0] === "" && a[0] !== "") return -1;
      return a[0].localeCompare(b[0]);
    });
    for (const [, itemsInLabel] of sortedLabelEntries) {
      itemsInLabel.sort((a, b) => a.name.localeCompare(b.name));
    }
    return sortedLabelEntries.map(([rawLabelKey, itemsInLabel]) => ({
      label: rawLabelKey === "" ? null : rawLabelKey,
      items: itemsInLabel,
    }));
  }, [metrics]);

  const defaultOpenLoggedMetricAccordionKeys = useMemo(
    () => loggedMetricsByLabel.map((g) => accordionItemValueForLoggedLabelGroup(g.label)),
    [loggedMetricsByLabel]
  );

  /**
   * When any tracked column has both this experiment and parent values, the metrics grid uses an
   * extra column for Δ vs parent (see `metricRowGroupTableClass`).
   */
  const trackedMetricsGridShowsParentDelta = useMemo(() => {
    if (!projectMetrics?.length || !experiment) return false;
    const currentAggregates = aggregatedMetricsByExperiment?.[experiment.id];
    const parentId = experiment.parentExperimentId;
    const parentAggregates =
      parentId != null ? aggregatedMetricsByExperiment?.[parentId] : undefined;
    return projectMetrics.some((trackedMetric) => {
      const currentValue = lookupAggregatedValueForTrackedMetric(currentAggregates, trackedMetric);
      const parentValue = lookupAggregatedValueForTrackedMetric(parentAggregates, trackedMetric);
      return currentValue != null && parentValue != null;
    });
  }, [projectMetrics, experiment, aggregatedMetricsByExperiment]);

  // Resolve the draft parent row for display (short id vs full label) in the trigger button.
  const {
    experiment: draftParentExperiment,
    isLoading: draftParentExperimentLoading,
  } = useExperiment(draftParentExperimentId || "");

  // Paginated list of sibling experiments — only fetched while the parent menu is open.
  const { experiments: projectExperiments, isLoading: projectExperimentsLoading } =
    useExperiments(experiment?.projectId, {
      enabled: (parentMenuOpen || featuresModalOpen) && !!experiment?.projectId,
      paginationMode: "auto",
      includeFeatures: featuresModalOpen,
    });

  // Parent picker rows: everyone in the project except the experiment being edited.
  const siblingExperimentsForParentPicker = useMemo(() => {
    if (!experiment) return [];
    return projectExperiments.filter((candidate) => candidate.id !== experiment.id);
  }, [projectExperiments, experiment]);

  /** Dropdown list after applying the search box (case-insensitive name or id substring). */
  const parentPickerRowsMatchingSearch = useMemo(() => {
    const queryNormalized = parentSearchQuery.trim().toLowerCase();
    if (!queryNormalized) return siblingExperimentsForParentPicker;
    return siblingExperimentsForParentPicker.filter((candidate) => {
      const menuLabel = formatExperimentParentOption(candidate).toLowerCase();
      return menuLabel.includes(queryNormalized) || candidate.id.toLowerCase().includes(queryNormalized);
    });
  }, [siblingExperimentsForParentPicker, parentSearchQuery]);

  /** Keep draft parent id in sync when switching to another experiment in the sidebar. */
  useLayoutEffect(() => {
    if (!experiment) return;
    setDraftParentExperimentId(experiment.parentExperimentId ?? null);
  }, [experiment?.id, experiment?.parentExperimentId]);

  // --- Mutations (edit form + status) ---
  const persistExperimentEdits = async (data: ExperimentEditSavePayload) => {
    if (!experiment) return;
    try {
      await updateExperiment(
        {
          name: data.name,
          description: data.description,
          color: data.color,
          ...(data.parentExperimentId !== undefined
            ? { parentExperimentId: data.parentExperimentId }
            : {}),
        },
        {
          onSuccess: () => {
            toast({
              title: "Experiment updated",
              description: "Changes have been saved.",
            });
          },
          onError: () => {
            toast({
              title: "Error",
              description: "Failed to update experiment.",
              variant: "destructive",
            });
          },
        }
      );
    } catch {
      toast({
        title: "Error",
        description: "Failed to update experiment.",
        variant: "destructive",
      });
    }
  };

  const selectParentExperimentFromMenu = (parentId: string) => {
    setDraftParentExperimentId(parentId);
    setParentMenuOpen(false);
  };

  const handleDownloadCurrentSnapshot = async () => {
    if (!experiment) return;
    setSnapshotDownloadPending(true);
    try {
      const { blob, filename } = await experimentSnapshotsService.download(experiment.id);
      downloadBlob(blob, filename || `${sanitizeDownloadName(experiment.name)}-snapshot.zip`);
      setDownloadSnapshotOpen(false);
      toast({ title: "Snapshot download started" });
    } catch {
      toast({
        title: "Failed to download snapshot",
        description: "The experiment may not have a logged snapshot yet.",
        variant: "destructive",
      });
    } finally {
      setSnapshotDownloadPending(false);
    }
  };

  const updateExperimentStatus = async (status: Experiment["status"]) => {
    if (!experiment) return;
    try {
      await updateExperiment(
        {
          status,
        },
        {
          onSuccess: () => {
            toast({
              title: "Status updated",
              description: "Experiment status has been updated.",
            });
          },
          onError: () => {
            toast({
              title: "Error",
              description: "Failed to update status.",
              variant: "destructive",
            });
          },
        }
      );
    } catch {
      toast({
        title: "Error",
        description: "Failed to update status.",
        variant: "destructive",
      });
    }
  };

  const persistExperimentTags = async (tags: string[]) => {
    if (!experiment) return;
    try {
      await updateExperiment(
        { tags },
        {
          onSuccess: () => {
            toast({
              title: "Tags updated",
              description: "Experiment tags have been saved.",
            });
          },
          onError: () => {
            toast({
              title: "Error",
              description: "Failed to update tags.",
              variant: "destructive",
            });
          },
        }
      );
    } catch {
      toast({
        title: "Error",
        description: "Failed to update tags.",
        variant: "destructive",
      });
    }
  };

  if (!experimentId) return null;

  /** Aggregates row list for the sidebar’s experiment (tracked metric values + parent deltas). */
  const currentExperimentAggregatedMetrics = experiment
    ? aggregatedMetricsByExperiment?.[experiment.id]
    : undefined;
  /** Same shape as above, for the saved parent experiment id (when present). */
  const parentExperimentAggregatedMetrics =
    experiment?.parentExperimentId != null
      ? aggregatedMetricsByExperiment?.[experiment.parentExperimentId]
      : undefined;

  return (
    <RightSidebarShell
      variant={variant}
      title={
        experimentLoading ? (
          <Skeleton className="h-5 w-32" />
        ) : (
          experiment?.name || "Experiment"
        )
      }
      headerPrefix={
        <div
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: experiment?.color || "#3b82f6" }}
        />
      }
      headerActions={
        <div className="flex items-center gap-1">
          {experiment && (
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              data-testid="button-open-experiment-details"
            >
              <Link
                href={FRONTEND_ROUTES.PROJECT_PAGES.EXPERIMENT_DETAILS(
                  experiment.projectId,
                  [experiment.id]
                )}
                target="_blank"
                rel="noopener noreferrer"
              >
                Details
              </Link>
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            disabled={experimentFetching || !experimentId}
            data-testid="button-refresh-experiment"
            aria-label="Refresh experiment"
          >
            <RefreshCw
              className={`w-4 h-4 ${experimentFetching ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      }
      onClose={onClose}
      widthClassName=""
      className="md:max-w-none"
      style={{ width: sidebarWidth }}
      onResizePointerDown={handleSidebarResizeStart}
      testId="experiment-sidebar"
    >
      {experimentLoading ? (
        <div className="p-4 space-y-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : experiment ? (
        <ScrollArea className="flex-1">
          <div className="min-w-0 max-w-full space-y-4 p-4">
            {/* Status + owning project (truncated on narrow sidebars) */}
            <div className="flex max-w-full min-w-0 flex-wrap items-center gap-2">
              <StatusBadge status={experiment.status} />
              {project && (
                <Badge variant="secondary" className="max-w-full min-w-0 truncate">
                  {project.name}
                </Badge>
              )}
              <ExperimentTagsEditor
                tags={experimentTags}
                disabled={updateIsPending}
                onChange={persistExperimentTags}
              />
            </div>

            {/* Parent lineage: choose another experiment in the project; saved with the edit form */}
            <div className="min-w-0 space-y-2">
              <p className="text-sm text-muted-foreground">Parent experiment</p>
              <div className="flex w-full min-w-0 max-w-full items-stretch gap-1 overflow-hidden">
                <DropdownMenu open={parentMenuOpen} onOpenChange={setParentMenuOpen}>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      disabled={updateIsPending}
                      data-testid="button-parent-experiment-menu"
                      className={cn(
                        "flex h-9 w-0 min-w-0 flex-1 items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-left text-sm shadow-sm ring-offset-background",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        "disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                    >
                      <GitBranch className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      {draftParentExperimentId &&
                      !draftParentExperimentLoading &&
                      draftParentExperiment ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="min-w-0 flex-1 truncate">
                              {formatExperimentParentOption(draftParentExperiment)}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-sm">
                            <p className="break-words text-sm">
                              {formatExperimentParentOption(draftParentExperiment)}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="min-w-0 flex-1 truncate">
                          {draftParentExperimentId ? (
                            draftParentExperimentLoading ? (
                              <Skeleton className="inline-block h-4 w-40 align-middle" />
                            ) : (
                              draftParentExperimentId.slice(0, 7)
                            )
                          ) : (
                            <span className="text-muted-foreground">No parent</span>
                          )}
                        </span>
                      )}
                      <ChevronDown className="h-4 w-4 shrink-0 opacity-50" aria-hidden />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="flex max-h-[min(40rem,calc(100dvh-2rem))] w-[min(36rem,calc(100vw-1.5rem))] flex-col overflow-hidden p-0"
                    align="start"
                    sideOffset={4}
                    onCloseAutoFocus={(e) => e.preventDefault()}
                  >
                    <div
                      className="shrink-0 border-b border-border p-2"
                      onPointerDown={(e) => e.preventDefault()}
                    >
                      <Input
                        ref={parentSearchInputRef}
                        type="search"
                        placeholder="Filter by name or id…"
                        value={parentSearchQuery}
                        onChange={(e) => setParentSearchQuery(e.target.value)}
                        className="h-9"
                        aria-label="Filter parent experiments"
                        autoComplete="off"
                        onKeyDown={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="max-h-[min(32rem,calc(100dvh-7rem))] min-h-0 flex-1 overflow-y-auto overscroll-contain p-1 [scrollbar-gutter:stable]">
                      {projectExperimentsLoading ? (
                        <div className="space-y-2 p-2">
                          <Skeleton className="h-9 w-full" />
                          <Skeleton className="h-9 w-full" />
                          <Skeleton className="h-9 w-full" />
                        </div>
                      ) : siblingExperimentsForParentPicker.length === 0 ? (
                        <p className="px-2 py-3 text-sm text-muted-foreground">
                          No other experiments in this project
                        </p>
                      ) : parentPickerRowsMatchingSearch.length === 0 ? (
                        <p className="px-2 py-3 text-sm text-muted-foreground">
                          No experiments match your filter
                        </p>
                      ) : (
                        parentPickerRowsMatchingSearch.map((candidate) => (
                          <DropdownMenuItem
                            key={candidate.id}
                            className="cursor-pointer"
                            onSelect={() => selectParentExperimentFromMenu(candidate.id)}
                          >
                            {formatExperimentParentOption(candidate)}
                          </DropdownMenuItem>
                        ))
                      )}
                    </div>
                  </DropdownMenuContent>
                </DropdownMenu>
                {draftParentExperimentId ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-9 w-9 shrink-0 border-input"
                    onClick={() => setDraftParentExperimentId(null)}
                    disabled={updateIsPending}
                    aria-label="Clear parent selection"
                    data-testid="button-clear-parent-experiment"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                ) : null}
              </div>
            </div>

            <ExperimentEditForm
              experiment={experiment}
              onSave={persistExperimentEdits}
              isSaving={updateIsPending}
              draftParentExperimentId={draftParentExperimentId}
              savedParentExperimentId={experiment.parentExperimentId ?? null}
            />

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Select
                value={experiment.status}
                onValueChange={(value) => updateExperimentStatus(value as Experiment["status"])}
              >
                <SelectTrigger className="w-32 h-8" data-testid="select-status">
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

            {experiment.status === "running" && (
              <div>
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                  <span>Progress</span>
                  <span>{experiment.progress}%</span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${experiment.progress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 text-sm">
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

            <EntityIdDisplay label="ID" value={experiment.id} />

            {/* Metrics / features / diff — keeps heavy JSON and git output out of the first paint path */}
            <Tabs
              value={activeTab}
              onValueChange={(value) => setActiveTab(value as ExperimentSidebarTab)}
              className="min-w-0 max-w-full space-y-2 overflow-hidden"
            >
              <TabsList className="w-full">
                <TabsTrigger value="metrics" className="flex-1" data-testid="tab-metrics">
                  Metrics
                </TabsTrigger>
                <TabsTrigger value="features" className="flex-1" data-testid="tab-features">
                  Features
                </TabsTrigger>
                <TabsTrigger value="hparams" className="flex-1" data-testid="tab-hparams">
                  HParams
                </TabsTrigger>
                <TabsTrigger value="code" className="flex-1" data-testid="tab-code">
                  Code
                </TabsTrigger>
              </TabsList>

              <TabsContent value="metrics" className="space-y-2">
                {/* Tracked metrics: one row per project definition; optional Δ vs parent when both aggregates exist */}
                {projectMetrics && projectMetrics.length > 0 ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Project Metrics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <div className={metricRowGroupTableClass(trackedMetricsGridShowsParentDelta)}>
                        {projectMetrics.map((projectMetric) => (
                          <MetricNameValueDiffRow
                            key={projectMetricKeyString(projectMetric)}
                            metricName={projectMetric.name}
                            metricLabel={projectMetric.label ?? null}
                            value={lookupAggregatedValueForTrackedMetric(
                              currentExperimentAggregatedMetrics,
                              projectMetric
                            )}
                            parentValue={lookupAggregatedValueForTrackedMetric(
                              parentExperimentAggregatedMetrics,
                              projectMetric
                            )}
                            direction={projectMetric.direction === "minimize" ? "minimize" : "maximize"}
                            showDirectionHint
                            metricTable={{
                              scope: "group",
                              groupHasAnyDiff: trackedMetricsGridShowsParentDelta,
                            }}
                            classNameProps={METRIC_SIDEBAR_DENSE_CLASS_NAMES}
                            data-testid={`metric-${projectMetricKeyString(projectMetric)}`}
                          />
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : null}

                {/* Logged scalars from ClickHouse: grouped by label; compare to parent only when the metric is tracked */}
                {metricsLoading ? (
                  <Skeleton className="h-24 w-full" />
                ) : metrics && metrics.length > 0 ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Logged Metrics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <Accordion
                        type="multiple"
                        className="w-full"
                        defaultValue={defaultOpenLoggedMetricAccordionKeys}
                      >
                        {loggedMetricsByLabel.map((labelGroup) => {
                          const accordionItemValue = accordionItemValueForLoggedLabelGroup(labelGroup.label);
                          const groupTitle =
                            labelGroup.label != null && labelGroup.label !== ""
                              ? labelGroup.label
                              : "Unlabeled";
                          const loggedLabelGroupShowsParentDelta = labelGroup.items.some((loggedMetric) => {
                            const trackedDefinition = findTrackedDefinitionForLoggedMetric(
                              trackedMetricDefinitions,
                              loggedMetric
                            );
                            if (!trackedDefinition) return false;
                            const parentScalar = lookupAggregatedValueForTrackedMetric(
                              parentLoggedMetrics,
                              trackedDefinition
                            );
                            return loggedMetric.value != null && parentScalar != null;
                          });
                          return (
                            <AccordionItem
                              key={accordionItemValue}
                              value={accordionItemValue}
                              className="border-border last:border-b-0"
                            >
                              <AccordionTrigger className="py-2 text-xs font-medium hover:no-underline">
                                <span className="truncate text-left">{groupTitle}</span>
                              </AccordionTrigger>
                              <AccordionContent className="pb-2 pt-0">
                                <div className={metricRowGroupTableClass(loggedLabelGroupShowsParentDelta)}>
                                  {labelGroup.items.map((loggedMetric) => {
                                    const trackedDefinition = findTrackedDefinitionForLoggedMetric(
                                      trackedMetricDefinitions,
                                      loggedMetric
                                    );
                                    if (trackedDefinition) {
                                      return (
                                        <MetricNameValueDiffRow
                                          key={loggedMetric.id}
                                          metricName={trackedDefinition.name}
                                          metricLabel={trackedDefinition.label ?? null}
                                          nameTitleMode="name-only"
                                          value={loggedMetric.value}
                                          parentValue={lookupAggregatedValueForTrackedMetric(
                                            parentLoggedMetrics,
                                            trackedDefinition
                                          )}
                                          direction={
                                            trackedDefinition.direction === "minimize"
                                              ? "minimize"
                                              : "maximize"
                                          }
                                          showDirectionHint
                                          metricTable={{
                                            scope: "group",
                                            groupHasAnyDiff: loggedLabelGroupShowsParentDelta,
                                          }}
                                          classNameProps={METRIC_SIDEBAR_DENSE_CLASS_NAMES}
                                          data-testid={`logged-metric-${loggedMetric.id}`}
                                        />
                                      );
                                    }
                                    return (
                                      <MetricNameValueDiffRow
                                        key={loggedMetric.id}
                                        metricName={loggedMetric.name}
                                        metricLabel={loggedMetric.label}
                                        nameTitleMode="name-only"
                                        value={loggedMetric.value}
                                        parentValue={null}
                                        direction="maximize"
                                        showDiff={false}
                                        metricTable={{
                                          scope: "group",
                                          groupHasAnyDiff: loggedLabelGroupShowsParentDelta,
                                        }}
                                        classNameProps={METRIC_SIDEBAR_UNTRACKED_CLASS_NAMES}
                                        data-testid={`logged-metric-${loggedMetric.id}`}
                                      />
                                    );
                                  })}
                                </div>
                              </AccordionContent>
                            </AccordionItem>
                          );
                        })}
                      </Accordion>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No metrics logged yet
                  </p>
                )}
              </TabsContent>

              <TabsContent value="features" className="min-w-0 max-w-full space-y-2 overflow-hidden">
                <ExperimentFeaturesPanel
                  experiment={experiment}
                  parentExperiment={savedParentExperiment}
                  projectExperiments={projectExperiments}
                  experimentsLoading={projectExperimentsLoading}
                  modalOpen={featuresModalOpen}
                  onModalOpenChange={setFeaturesModalOpen}
                  lockExperimentFeaturesSelection
                  showDiffs={featureDiffsEnabled}
                  onShowDiffsChange={setFeatureDiffsEnabled}
                />
              </TabsContent>

              <TabsContent value="hparams" className="min-w-0 max-w-full space-y-2 overflow-hidden">
                <ExperimentHparamsPanel
                  experimentId={experiment.id}
                  parentExperimentId={experiment.parentExperimentId}
                  enabled={activeTab === "hparams"}
                />
              </TabsContent>

              <TabsContent value="code" className="space-y-2">
                <div className="space-y-2 rounded-md border bg-muted/20 p-3">
                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    data-testid="button-open-code-compare"
                  >
                    <Link
                      href={buildCodeCompareHref(experiment)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <GitCompare className="h-4 w-4" />
                      <span>{experiment.parentExperimentId ? "Open code compare" : "Open files"}</span>
                    </Link>
                  </Button>
                  {experiment.parentExperimentId ? (
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      className="w-full justify-start"
                      data-testid="button-open-code-files"
                    >
                      <Link
                        href={buildCodeFilesHref(experiment)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <FileCode2 className="h-4 w-4" />
                        <span>Open files</span>
                      </Link>
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    data-testid="button-download-snapshot"
                    onClick={() => setDownloadSnapshotOpen(true)}
                  >
                    <Download className="h-4 w-4" />
                    <span>Download snapshot</span>
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      ) : (
        <div className="p-4 text-center text-muted-foreground">
          Experiment not found
        </div>
      )}
      <Dialog
        open={downloadSnapshotOpen}
        onOpenChange={(open) => !snapshotDownloadPending && setDownloadSnapshotOpen(open)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Download snapshot?</DialogTitle>
            <DialogDescription>
              This will download the current file snapshot for{" "}
              {experiment?.name ?? "this experiment"} as a ZIP archive.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
            <div className="truncate font-medium text-foreground">{experiment?.name}</div>
            <div className="break-all">{experiment?.id}</div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={snapshotDownloadPending}
              onClick={() => setDownloadSnapshotOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={snapshotDownloadPending}
              onClick={handleDownloadCurrentSnapshot}
            >
              {snapshotDownloadPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Download
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </RightSidebarShell>
  );
}
