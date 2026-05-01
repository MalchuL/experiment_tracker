import Link from "next/link";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  ExperimentEditForm,
  type ExperimentEditSavePayload,
} from "@/components/shared/experiment-edit-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RightSidebarShell } from "@/components/shared/right-sidebar-shell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
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
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useExperiment } from "@/domain/experiments/hooks/experiment-hook";
import { useExperiments } from "@/domain/experiments/hooks/experiments-hook";
import {
  GitBranch,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  X,
  ChevronDown,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type { Metric } from "@/domain/metrics/types";
import type { ProjectMetric } from "@/domain/projects/types";
import { useExperimentMetrics } from "@/domain/metrics/hooks";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { REFRESH_EXPERIMENT_SIDEBAR_INTERVAL } from "@/lib/constants/rates";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { cn } from "@/lib/utils";
import { displayMetricKeyEquals, formatMetricLabel, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function formatExperimentParentOption(exp: Pick<Experiment, "name" | "id">): string {
  return `${exp.name} (${exp.id.slice(0, 7)})`;
}

interface ExperimentSidebarProps {
  experimentId: string | null;
  onClose: () => void;
  projectMetrics?: ProjectMetric[];
  aggregatedMetrics?: Metric[];
}

export function ExperimentSidebar({
  experimentId,
  onClose,
  projectMetrics,
  aggregatedMetrics,
}: ExperimentSidebarProps) {
  const { toast } = useToast();
  const [parentMenuOpen, setParentMenuOpen] = useState(false);
  const [parentFilter, setParentFilter] = useState("");
  const parentFilterInputRef = useRef<HTMLInputElement>(null);
  const [draftParentExperimentId, setDraftParentExperimentId] = useState<string | null>(null);

  useEffect(() => {
    if (!parentMenuOpen) {
      setParentFilter("");
      return;
    }
    requestAnimationFrame(() => parentFilterInputRef.current?.focus());
  }, [parentMenuOpen]);

  const {
    experiment,
    isLoading: experimentLoading,
    isFetching: experimentFetching,
    updateIsPending,
    updateExperiment,
    refetch,
  } = useExperiment(experimentId || "", { refetchInterval: REFRESH_EXPERIMENT_SIDEBAR_INTERVAL });

  const { metrics, isLoading: metricsLoading } = useExperimentMetrics(experimentId || "");
  const { project } = useProject(experiment?.projectId);

  const loggedMetricsByLabel = useMemo(() => {
    if (!metrics?.length) {
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
    return entries.map(([k, items]) => ({ label: k === "" ? null : k, items }));
  }, [metrics]);

  const {
    experiment: draftParentExperiment,
    isLoading: draftParentExperimentLoading,
  } = useExperiment(draftParentExperimentId || "");

  const { experiments: projectExperiments, isLoading: projectExperimentsLoading } =
    useExperiments(experiment?.projectId, {
      enabled: parentMenuOpen && !!experiment?.projectId,
      paginationMode: "auto",
    });

  const parentCandidates = useMemo(() => {
    if (!experiment) return [];
    return projectExperiments.filter((e) => e.id !== experiment.id);
  }, [projectExperiments, experiment]);

  const filteredParentCandidates = useMemo(() => {
    const q = parentFilter.trim().toLowerCase();
    if (!q) return parentCandidates;
    return parentCandidates.filter((e) => {
      const label = formatExperimentParentOption(e).toLowerCase();
      return label.includes(q) || e.id.toLowerCase().includes(q);
    });
  }, [parentCandidates, parentFilter]);

  useLayoutEffect(() => {
    if (!experiment) return;
    setDraftParentExperimentId(experiment.parentExperimentId ?? null);
  }, [experiment?.id, experiment?.parentExperimentId]);

  const handleSaveForm = async (data: ExperimentEditSavePayload) => {
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

  const handleDraftParentSelect = (parentId: string) => {
    setDraftParentExperimentId(parentId);
    setParentMenuOpen(false);
  };

  const handleStatusChange = async (status: Experiment["status"]) => {
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

  if (!experimentId) return null;

  const formatMetricValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "NaN";
    return value.toFixed(4);
  };

  return (
    <RightSidebarShell
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
          <div className="p-4 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={experiment.status} />
              {project && (
                <Badge variant="secondary">{project.name}</Badge>
              )}
            </div>

            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Parent experiment</p>
              <div className="flex w-full items-stretch gap-1">
                <DropdownMenu open={parentMenuOpen} onOpenChange={setParentMenuOpen}>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      disabled={updateIsPending}
                      data-testid="button-parent-experiment-menu"
                      className={cn(
                        "flex h-9 min-w-0 flex-1 items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-left text-sm shadow-sm ring-offset-background",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        "disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                    >
                      <GitBranch className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">
                        {draftParentExperimentId ? (
                          draftParentExperimentLoading ? (
                            <Skeleton className="inline-block h-4 w-40 align-middle" />
                          ) : draftParentExperiment ? (
                            formatExperimentParentOption(draftParentExperiment)
                          ) : (
                            draftParentExperimentId.slice(0, 7)
                          )
                        ) : (
                          <span className="text-muted-foreground">No parent</span>
                        )}
                      </span>
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
                        ref={parentFilterInputRef}
                        type="search"
                        placeholder="Filter by name or id…"
                        value={parentFilter}
                        onChange={(e) => setParentFilter(e.target.value)}
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
                      ) : parentCandidates.length === 0 ? (
                        <p className="px-2 py-3 text-sm text-muted-foreground">
                          No other experiments in this project
                        </p>
                      ) : filteredParentCandidates.length === 0 ? (
                        <p className="px-2 py-3 text-sm text-muted-foreground">
                          No experiments match your filter
                        </p>
                      ) : (
                        filteredParentCandidates.map((exp) => (
                          <DropdownMenuItem
                            key={exp.id}
                            className="cursor-pointer"
                            onSelect={() => handleDraftParentSelect(exp.id)}
                          >
                            {formatExperimentParentOption(exp)}
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
              onSave={handleSaveForm}
              isSaving={updateIsPending}
              draftParentExperimentId={draftParentExperimentId}
              savedParentExperimentId={experiment.parentExperimentId ?? null}
            />

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Select
                value={experiment.status}
                onValueChange={(value) => handleStatusChange(value as Experiment["status"])}
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
                  {format(parseISO(experiment.createdAt), "MMM d, yyyy")}
                </p>
              </div>
              <div className="p-2 rounded-md bg-muted/50">
                <p className="text-muted-foreground text-xs">Started</p>
                <p className="font-medium">
                  {experiment.startedAt
                    ? format(parseISO(experiment.startedAt), "MMM d, HH:mm")
                    : "-"}
                </p>
              </div>
            </div>

            <div className="text-xs font-mono text-muted-foreground p-2 bg-muted/50 rounded-md">
              ID: {experiment.id}
            </div>

            <Tabs defaultValue="metrics" className="space-y-2">
              <TabsList className="w-full">
                <TabsTrigger value="metrics" className="flex-1" data-testid="tab-metrics">
                  Metrics
                </TabsTrigger>
                <TabsTrigger value="features" className="flex-1" data-testid="tab-features">
                  Features
                </TabsTrigger>
                <TabsTrigger value="code" className="flex-1" data-testid="tab-code">
                  Code
                </TabsTrigger>
              </TabsList>

              <TabsContent value="metrics" className="space-y-2">
                {projectMetrics && projectMetrics.length > 0 ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Project Metrics
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <div className="space-y-2">
                        {projectMetrics.map((pm) => {
                          const value = aggregatedMetrics?.find((m) =>
                            displayMetricKeyEquals(
                              { name: m.name, label: m.label },
                              { name: pm.name, label: pm.label ?? null }
                            )
                          )?.value;
                          return (
                            <div
                              key={projectMetricKeyString(pm)}
                              className="flex items-center justify-between text-sm"
                              data-testid={`metric-${projectMetricKeyString(pm)}`}
                            >
                              <div className="flex items-center gap-2">
                                <span>{formatMetricLabel(pm.name, pm.label ?? null)}</span>
                                {pm.direction === "minimize" ? (
                                  <TrendingDown className="w-3 h-3 text-muted-foreground" />
                                ) : (
                                  <TrendingUp className="w-3 h-3 text-muted-foreground" />
                                )}
                              </div>
                              <span
                                className={`font-mono ${
                                  value === null || value === undefined
                                    ? "text-muted-foreground"
                                    : ""
                                }`}
                              >
                                {formatMetricValue(value)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                ) : null}

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
                      <div className="space-y-3">
                        {loggedMetricsByLabel.map((group) => (
                          <div key={group.label ?? "unlabeled"} className="space-y-1.5">
                            {group.label != null ? (
                              <p className="text-[10px] font-medium text-muted-foreground">
                                {group.label}
                              </p>
                            ) : (
                              <p className="text-[10px] font-medium text-muted-foreground">
                                Unlabeled
                              </p>
                            )}
                            {group.items.map((metric) => (
                              <div
                                key={metric.id}
                                className="flex items-center justify-between text-sm pl-0"
                                data-testid={`logged-metric-${metric.id}`}
                              >
                                <span className="truncate pr-2">{metric.name}</span>
                                <span className="font-mono flex-shrink-0">
                                  {metric.value.toFixed(4)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No metrics logged yet
                  </p>
                )}
              </TabsContent>

              <TabsContent value="features" className="space-y-2">
                <Card>
                  <CardHeader className="py-2 px-3">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Full Features
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-3 pb-3 pt-0">
                    <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-32">
                      {JSON.stringify(experiment.features, null, 2) ||
                        "No features"}
                    </pre>
                  </CardContent>
                </Card>

                {experiment.featuresDiff && (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Features Diff
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(experiment.featuresDiff, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="code" className="space-y-2">
                {experiment.gitDiff ? (
                  <Card>
                    <CardHeader className="py-2 px-3">
                      <CardTitle className="text-xs font-medium text-muted-foreground">
                        Git Diff
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 pt-0">
                      <pre className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-48 whitespace-pre-wrap">
                        {experiment.gitDiff}
                      </pre>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No code diff captured
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      ) : (
        <div className="p-4 text-center text-muted-foreground">
          Experiment not found
        </div>
      )}
    </RightSidebarShell>
  );
}
