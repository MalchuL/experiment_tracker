"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/shared/page-header";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useExperiments } from "@/domain/experiments/hooks";
import { useProjectScalars } from "@/domain/scalars/hooks";
import { ScalarViewsSidebar } from "@/domain/scalars/components";
import { AlertCircle, BarChart3, ChevronDown, Eye, EyeOff, Maximize2, Pencil, RotateCcw } from "lucide-react";
import Plot from "react-plotly.js";
import type { Layout, Config } from "plotly.js";
import type { Experiment } from "@/domain/experiments/types";
import { ExperimentEditForm } from "@/components/shared/experiment-edit-form";
import { experimentsService } from "@/domain/experiments/services";
import type { UpdateExperiment } from "@/domain/experiments/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

const CHART_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#22c55e",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
  "#84cc16",
  "#14b8a6",
];

type SyncMode = "all" | "x-only" | "y-only" | "independent";

interface ChartDomain {
  x: [number, number] | null;
  y: [number, number] | null;
}

function encodeSelection(indices: number[]): string {
  if (indices.length === 0) return "";
  return btoa(indices.join(","));
}

function decodeSelection(encoded: string): number[] {
  if (!encoded) return [];
  try {
    return atob(encoded).split(",").map(Number).filter(n => !isNaN(n));
  } catch {
    return [];
  }
}

function applySmoothing(data: number[], weight: number): number[] {
  if (weight === 0 || data.length === 0) return data;
  const smoothed: number[] = [];
  let last = data[0];
  for (const value of data) {
    const smoothedValue = last * weight + value * (1 - weight);
    smoothed.push(smoothedValue);
    last = smoothedValue;
  }
  return smoothed;
}

interface MetricChartProps {
  metricName: string;
  data: Array<Record<string, number | null>>;
  experiments: Experiment[];
  selectedExperiments: Experiment[];
  allExperiments: Experiment[];
  height?: number;
  showBrush?: boolean;
  domain?: ChartDomain | null;
  onDomainChange?: (domain: ChartDomain | null) => void;
  onExpand?: () => void;
  onReset?: () => void;
  isFullscreen?: boolean;
}

function MetricChart({
  metricName,
  data,
  selectedExperiments,
  allExperiments,
  height = 200,
  domain,
  onDomainChange,
  isFullscreen = false,
}: MetricChartProps) {
  const [dragMode, setDragMode] = useState<"zoom" | "pan">("zoom");
  const plotData = useMemo(() => {
    return selectedExperiments.map((experiment) => {
      const originalIndex = allExperiments.findIndex(e => e.id === experiment.id);
      const experimentColor = experiment.color || CHART_COLORS[originalIndex % CHART_COLORS.length];
      const xValues: number[] = [];
      const yValues: number[] = [];
      
      data.forEach(point => {
        const step = point.step as number;
        // Key by experiment ID to avoid collisions when experiment names are duplicated.
        const value = point[experiment.id];
        if (value !== null && value !== undefined) {
          xValues.push(step);
          yValues.push(value as number);
        }
      });

      return {
        x: xValues,
        y: yValues,
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: experiment.name,
        line: {
          color: experimentColor,
          width: isFullscreen ? 2 : 1.5,
        },
        hovertemplate: `<b>${experiment.name}</b><br>Step: %{x}<br>Value: %{y:.4f}<extra></extra>`,
      };
    });
  }, [data, selectedExperiments, allExperiments, isFullscreen]);

  const handleRelayout = useCallback((event: any) => {
    if (event?.dragmode) {
      setDragMode(event.dragmode);
    }
    const nextDomain: ChartDomain = {
      x: domain?.x ?? null,
      y: domain?.y ?? null,
    };

    if (event["xaxis.range[0]"] !== undefined && event["xaxis.range[1]"] !== undefined) {
      nextDomain.x = [event["xaxis.range[0]"], event["xaxis.range[1]"]];
    } else if (event["xaxis.autorange"] === true) {
      nextDomain.x = null;
    }

    if (event["yaxis.range[0]"] !== undefined && event["yaxis.range[1]"] !== undefined) {
      nextDomain.y = [event["yaxis.range[0]"], event["yaxis.range[1]"]];
    } else if (event["yaxis.autorange"] === true) {
      nextDomain.y = null;
    }

    onDomainChange?.(nextDomain);
  }, [domain, onDomainChange]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data for selected experiments
      </div>
    );
  }

  const layout: Partial<Layout> = {
    autosize: true,
    height,
    margin: {
      l: isFullscreen ? 60 : 50,
      r: 20,
      t: 10,
      b: isFullscreen ? 40 : 30,
    },
    xaxis: {
      title: isFullscreen ? { text: 'Step', font: { size: 12 } } : undefined,
      tickfont: { size: isFullscreen ? 12 : 10 },
      gridcolor: 'rgba(128, 128, 128, 0.2)',
      range: domain?.x || undefined,
      autorange: domain?.x ? false : true,
    },
    yaxis: {
      tickfont: { size: isFullscreen ? 12 : 10 },
      gridcolor: 'rgba(128, 128, 128, 0.2)',
      range: domain?.y || undefined,
      autorange: domain?.y ? false : true,
    },
    showlegend: false,
    hovermode: 'x unified' as const,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    dragmode: dragMode,
  };

  const config: Partial<Config> = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'] as any,
    displaylogo: false,
    responsive: true,
  };

  return (
    <div style={{ height }}>
      <Plot
        data={plotData}
        layout={layout}
        config={config}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        onRelayout={handleRelayout}
      />
    </div>
  );
}

export default function Scalars() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const searchParams = useSearchParams();
  
  const [smoothing, setSmoothing] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const [selectedExperimentIndices, setSelectedExperimentIndices] = useState<Set<number>>(new Set());
  const [hiddenMetrics, setHiddenMetrics] = useState<Set<string>>(new Set());
  const [metricDomains, setMetricDomains] = useState<Record<string, ChartDomain>>({});
  const [fullscreenMetric, setFullscreenMetric] = useState<string | null>(null);
  const [syncMode, setSyncMode] = useState<SyncMode>("all");
  const [soloMode, setSoloMode] = useState(false);
  const [chosenExperimentId, setChosenExperimentId] = useState<string | null>(null);
  const [viewsSidebarOpen, setViewsSidebarOpen] = useState(true);
  const [editExperiment, setEditExperiment] = useState<Experiment | null>(null);
  const [cardHeight, setCardHeight] = useState(220);
  const [cardMinWidth, setCardMinWidth] = useState(320);

  const queryClient = useQueryClient();
  const updateExperiment = useMutation({
    mutationFn: (payload: { id: string; data: UpdateExperiment }) =>
      experimentsService.update(payload.id, payload.data as any),
    onSuccess: () => {
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: [QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId)],
        });
      }
    },
  });

  const {
    experiments = [],
    isLoading: experimentsLoading,
    isFetching: experimentsFetching,
    refetch: refetchExperiments,
  } = useExperiments(projectId);

  const {
    scalars,
    isLoading: scalarsLoading,
    isFetching: scalarsFetching,
    refetch: refetchScalars,
  } = useProjectScalars({
    projectId,
    returnTags: false,
  });

  const allLoggedMetricNames = useMemo(() => {
    const metricSet = new Set<string>();
    scalars.forEach((experimentScalars) => {
      Object.keys(experimentScalars.scalars || {}).forEach((name) => metricSet.add(name));
    });
    return Array.from(metricSet).sort();
  }, [scalars]);

  const safeDecodeIndices = useCallback((encoded: string | null): number[] => {
    if (!encoded) return [];
    try {
      return decodeSelection(encoded).filter((value) => Number.isInteger(value));
    } catch {
      return [];
    }
  }, []);

  const applySharedParams = useCallback((params: URLSearchParams) => {
    try {
      const expParam = params.get("exp");
      const metParam = params.get("met");
      const smoothParam = params.get("s");

      if (expParam) {
        const indices = safeDecodeIndices(expParam);
        setSelectedExperimentIndices(
          new Set(indices.filter((i) => i >= 0 && i < experiments.length))
        );
      } else {
        setSelectedExperimentIndices(new Set(experiments.map((_, i) => i)));
      }

      if (metParam) {
        const hiddenIndices = safeDecodeIndices(metParam);
        const hiddenNames = hiddenIndices
          .map((i) => allLoggedMetricNames[i])
          .filter((name): name is string => typeof name === "string");
        setHiddenMetrics(new Set(hiddenNames));
      } else {
        setHiddenMetrics(new Set());
      }

      if (smoothParam) {
        const s = parseFloat(smoothParam);
        if (!isNaN(s) && s >= 0 && s <= 1) {
          setSmoothing(s);
          return;
        }
      }
      setSmoothing(0);
    } catch {
      // If saved/shared params are malformed, fall back to safe defaults.
      setSelectedExperimentIndices(new Set(experiments.map((_, i) => i)));
      setHiddenMetrics(new Set());
      setSmoothing(0);
    }
  }, [experiments, allLoggedMetricNames, safeDecodeIndices]);

  useEffect(() => {
    if (experiments.length === 0 || initialized) return;

    const hasMetricsParam = !!searchParams.get("met");
    if (hasMetricsParam && allLoggedMetricNames.length === 0) {
      return;
    }
    applySharedParams(new URLSearchParams(searchParams.toString()));
    setInitialized(true);
  }, [experiments, searchParams, initialized, allLoggedMetricNames, applySharedParams]);

  const buildQueryString = useCallback((expIndices: Set<number>, hiddenMets: Set<string>, smooth: number) => {
    const params = new URLSearchParams();
    
    const allSelected = expIndices.size === experiments.length;
    if (!allSelected && expIndices.size > 0) {
      params.set("exp", encodeSelection(Array.from(expIndices).sort()));
    }
    
    if (hiddenMets.size > 0) {
      const hiddenIndices = Array.from(hiddenMets)
        .map(name => allLoggedMetricNames.indexOf(name))
        .filter(i => i >= 0)
        .sort();
      if (hiddenIndices.length > 0) {
        params.set("met", encodeSelection(hiddenIndices));
      }
    }
    
    if (smooth > 0) {
      params.set("s", smooth.toFixed(2));
    }
    
    return params.toString();
  }, [experiments.length, allLoggedMetricNames]);

  const currentQueryString = useMemo(
    () => buildQueryString(selectedExperimentIndices, hiddenMetrics, smoothing),
    [buildQueryString, selectedExperimentIndices, hiddenMetrics, smoothing]
  );

  useEffect(() => {
    if (!initialized || !projectId) return;
    const nextQuery = buildQueryString(
      selectedExperimentIndices,
      hiddenMetrics,
      smoothing
    );
    const currentQuery = new URLSearchParams(window.location.search).toString();
    if (nextQuery === currentQuery) return;
    const basePath = `/projects/${projectId}/scalars`;
    // Keep URL shareable without triggering router navigation/re-render cycles.
    window.history.replaceState(
      window.history.state,
      "",
      nextQuery ? `${basePath}?${nextQuery}` : basePath
    );
  }, [
    initialized,
    projectId,
    selectedExperimentIndices,
    hiddenMetrics,
    smoothing,
    buildQueryString,
  ]);

  const toggleExperiment = (index: number) => {
    setSelectedExperimentIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const selectAllExperiments = () => {
    const all = new Set(experiments.map((_, i) => i));
    setSelectedExperimentIndices(all);
  };

  const clearAllExperiments = () => {
    setSelectedExperimentIndices(new Set());
  };

  const toggleMetric = (metricName: string) => {
    setHiddenMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(metricName)) {
        next.delete(metricName);
      } else {
        next.add(metricName);
      }
      return next;
    });
  };

  const showAllMetrics = () => {
    setHiddenMetrics(new Set());
  };

  const showOnlyMetric = (metricName: string) => {
    if (allLoggedMetricNames.length === 0) return;
    const newHidden = new Set(allLoggedMetricNames.filter(name => name !== metricName));
    setHiddenMetrics(newHidden);
  };

  const handleSmoothingChange = (value: number[]) => {
    setSmoothing(value[0]);
  };

  const handleSmoothingCommit = (_value: number[]) => {};

  const handleRestoreSavedView = useCallback((query: string) => {
    const normalizedQuery = query.startsWith("?") ? query.slice(1) : query;
    const params = new URLSearchParams(normalizedQuery);
    applySharedParams(params);
    if (projectId) {
      const basePath = `/projects/${projectId}/scalars`;
      window.history.replaceState(
        window.history.state,
        "",
        normalizedQuery ? `${basePath}?${normalizedQuery}` : basePath
      );
    }
  }, [applySharedParams, projectId]);

  const handleDomainChange = (metricName: string, domain: ChartDomain | null) => {
    setMetricDomains(prev => {
      const nextDomain = domain ?? { x: null, y: null };
      if (syncMode === "independent") {
        return { ...prev, [metricName]: nextDomain };
      }
      const next: Record<string, ChartDomain> = { ...prev };
      const metricNames = visibleMetrics.map((metric) => metric.name);
      metricNames.forEach((name) => {
        const current = next[name] ?? { x: null, y: null };
        if (syncMode === "x-only") {
          next[name] = { x: nextDomain.x, y: current.y };
        } else if (syncMode === "y-only") {
          next[name] = { x: current.x, y: nextDomain.y };
        } else {
          next[name] = { x: nextDomain.x, y: nextDomain.y };
        }
      });
      return next;
    });
  };

  const resetDomain = (metricName: string) => {
    handleDomainChange(metricName, { x: null, y: null });
  };

  const resetAllDomains = () => {
    const next: Record<string, ChartDomain> = {};
    visibleMetrics.forEach((metric) => {
      next[metric.name] = { x: null, y: null };
    });
    setMetricDomains(next);
  };

  const visibleMetrics = useMemo(() => {
    if (allLoggedMetricNames.length === 0) return [];
    return allLoggedMetricNames
      .filter(name => !hiddenMetrics.has(name))
      .map(name => ({ name }));
  }, [allLoggedMetricNames, hiddenMetrics]);

  const selectedExperiments = useMemo(() => {
    return experiments.filter((_, i) => selectedExperimentIndices.has(i));
  }, [experiments, selectedExperimentIndices]);

  const visibleExperiments = useMemo(() => {
    if (soloMode) {
      if (chosenExperimentId) {
        return experiments.filter((experiment) => experiment.id === chosenExperimentId);
      }
      // In solo mode without a chosen experiment, fall back to normal selection.
      return selectedExperiments;
    }

    return selectedExperiments;
  }, [soloMode, chosenExperimentId, experiments, selectedExperiments]);

  useEffect(() => {
    if (soloMode) return;
    setChosenExperimentId(null);
  }, [soloMode]);

  useEffect(() => {
    if (!chosenExperimentId) return;
    const stillExists = experiments.some((experiment) => experiment.id === chosenExperimentId);
    if (!stillExists) {
      setChosenExperimentId(null);
    }
  }, [experiments, chosenExperimentId]);

  const toggleSoloMode = () => {
    setSoloMode((prev) => !prev);
  };

  const chartDataByMetric = useMemo(() => {
    const result: Record<string, Array<Record<string, number | null>>> = {};
    
    if (scalars.length === 0 || visibleExperiments.length === 0) return result;

    const scalarsByExperiment = new Map(
      scalars.map((entry) => [entry.experiment_id, entry.scalars])
    );

    for (const metric of visibleMetrics) {
      const stepMap = new Map<number, Record<string, number | null>>();
      
      visibleExperiments.forEach((experiment) => {
        const experimentScalars = scalarsByExperiment.get(experiment.id);
        const series = experimentScalars?.[metric.name];
        if (!series || series.x.length === 0 || series.y.length === 0) {
          return;
        }

        const smoothedValues = applySmoothing(series.y, smoothing);
        series.x.forEach((step, i) => {
          const existing = stepMap.get(step) || { step };
          // Persist data under stable experiment IDs; labels remain human-readable names.
          existing[experiment.id] = smoothedValues[i];
          stepMap.set(step, existing);
        });
      });

      result[metric.name] = Array.from(stepMap.values()).sort(
        (a, b) => (a.step as number) - (b.step as number)
      );
    }

    return result;
  }, [scalars, visibleExperiments, visibleMetrics, smoothing]);

  const fullscreenMetricData = fullscreenMetric ? chartDataByMetric[fullscreenMetric] || [] : [];

  const refreshButton = (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        void (async () => {
          const hadAllSelected = selectedExperimentIndices.size === experiments.length;
          // Refresh experiments first so newly created runs are available for charting.
          await refetchExperiments();
          await refetchScalars();

          // Keep "all selected" semantics when new experiments appear after refresh.
          if (hadAllSelected && projectId) {
            const refreshedExperiments =
              queryClient.getQueryData<Experiment[]>([
                QUERY_KEYS.EXPERIMENTS.BY_PROJECT(projectId),
              ]) ?? [];
            const allIndices = new Set(refreshedExperiments.map((_, index) => index));
            setSelectedExperimentIndices(allIndices);
          }
        })();
      }}
      disabled={scalarsFetching || experimentsFetching}
      data-testid="button-refresh-scalars"
    >
      <RotateCcw
        className={`w-4 h-4 mr-2 ${scalarsFetching || experimentsFetching ? "animate-spin" : ""}`}
      />
      {scalarsFetching || experimentsFetching ? "Refreshing..." : "Refresh"}
    </Button>
  );

  const pageActions = (
    <div className="flex items-center gap-2">
      {refreshButton}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setViewsSidebarOpen((prev) => !prev)}
        data-testid="button-toggle-views-sidebar"
      >
        {viewsSidebarOpen ? "Hide Views" : "Show Views"}
      </Button>
    </div>
  );

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No Project Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Click on the logo in the sidebar to select a project and view its metrics.
        </p>
      </div>
    );
  }

  if (projectLoading || experimentsLoading || scalarsLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Scalars"
          description="Compare scalars across experiments"
          actions={pageActions}
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  const gridCols = visibleMetrics.length === 1 ? 1 : visibleMetrics.length === 2 ? 2 : 
    visibleMetrics.length <= 4 ? 2 : 3;

  return (
    <div className={`flex h-[calc(100vh-5rem)] gap-4 ${viewsSidebarOpen ? "pr-80" : ""}`}>
      <Card className="w-72 flex-shrink-0 flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Controls</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col gap-4">
          <div className="space-y-2">
            <Label className="text-sm font-medium">Sync Mode</Label>
            <select
              value={syncMode}
              onChange={(event) => setSyncMode(event.target.value as SyncMode)}
              className="w-full px-2 py-1 text-xs border border-border rounded bg-background text-foreground"
              data-testid="select-sync-mode"
            >
              <option value="all">All (X & Y)</option>
              <option value="x-only">X-Axis Only</option>
              <option value="y-only">Y-Axis Only</option>
              <option value="independent">Independent</option>
            </select>
            <Button
              variant={soloMode ? "default" : "outline"}
              size="sm"
              onClick={toggleSoloMode}
              className="w-full text-xs"
              data-testid="button-solo-mode"
            >
              {soloMode ? "✓ Solo Mode" : "Solo Mode"}
            </Button>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label className="text-sm font-medium">Card Size</Label>
            <div className="flex items-center gap-3">
              <Slider
                value={[cardHeight]}
                onValueChange={(value) => setCardHeight(value[0])}
                min={180}
                max={420}
                step={10}
                className="flex-1"
                data-testid="slider-card-size"
              />
              <span className="text-sm font-mono w-12 text-right">
                {cardHeight}px
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Card Width</Label>
            <div className="flex items-center gap-3">
              <Slider
                value={[cardMinWidth]}
                onValueChange={(value) => setCardMinWidth(value[0])}
                min={240}
                max={560}
                step={20}
                className="flex-1"
                data-testid="slider-card-width"
              />
              <span className="text-sm font-mono w-12 text-right">
                {cardMinWidth}px
              </span>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label className="text-sm font-medium">Smoothing</Label>
            <div className="flex items-center gap-3">
              <Slider
                value={[smoothing]}
                onValueChange={handleSmoothingChange}
                onValueCommit={handleSmoothingCommit}
                min={0}
                max={0.99}
                step={0.01}
                className="flex-1"
                data-testid="slider-smoothing"
              />
              <span className="text-sm font-mono w-10 text-right">
                {smoothing.toFixed(2)}
              </span>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label className="text-sm font-medium">Experiments</Label>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={selectAllExperiments}
                  data-testid="button-select-all-experiments"
                >
                  All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={clearAllExperiments}
                  data-testid="button-clear-all-experiments"
                >
                  None
                </Button>
              </div>
            </div>
            <ScrollArea className="h-40">
              <div className="space-y-1 pr-3">
                {experiments.map((experiment, index) => (
                  <div
                    key={experiment.id}
                    className="flex items-center gap-2 py-1"
                  >
                    {soloMode && (
                      <button
                        type="button"
                        onClick={() => setChosenExperimentId(experiment.id)}
                        className={`h-3 w-3 rounded-full border flex-shrink-0 transition-colors ${
                          chosenExperimentId === experiment.id
                            ? "border-primary bg-primary"
                            : "border-muted-foreground/50 bg-transparent"
                        }`}
                        aria-label={`Choose ${experiment.name} for solo mode`}
                        data-testid={`button-solo-experiment-${index}`}
                      />
                    )}
                    <Checkbox
                      id={`exp-${index}`}
                      checked={selectedExperimentIndices.has(index)}
                      onCheckedChange={() => toggleExperiment(index)}
                      data-testid={`checkbox-experiment-${index}`}
                    />
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: experiment.color || CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                    <label
                      htmlFor={`exp-${index}`}
                      className="text-sm truncate cursor-pointer flex-1"
                      title={experiment.name}
                    >
                      {experiment.name}
                    </label>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => setEditExperiment(experiment)}
                      data-testid={`button-edit-experiment-${index}`}
                    >
                      <Pencil className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          <Separator />

          <div className="space-y-2 flex-1 min-h-0">
            <div className="flex items-center justify-between gap-2">
              <Label className="text-sm font-medium">Scalars</Label>
              {hiddenMetrics.size > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={showAllMetrics}
                  data-testid="button-show-all-metrics"
                >
                  Show All
                </Button>
              )}
            </div>
            <ScrollArea className="h-32">
              <div className="space-y-1 pr-3">
                {allLoggedMetricNames.map((metricName) => (
                  <div
                    key={metricName}
                    className="flex items-center gap-1 py-1"
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 flex-shrink-0"
                      onClick={() => toggleMetric(metricName)}
                      data-testid={`button-toggle-metric-${metricName}`}
                    >
                      {hiddenMetrics.has(metricName) ? (
                        <EyeOff className="w-3 h-3 text-muted-foreground" />
                      ) : (
                        <Eye className="w-3 h-3" />
                      )}
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <div
                          className="flex items-center gap-1 flex-1 min-w-0 px-1 py-0.5 rounded-md cursor-pointer hover-elevate"
                          data-testid={`dropdown-metric-${metricName}`}
                        >
                          <span 
                            className={`text-sm truncate flex-1 ${hiddenMetrics.has(metricName) ? 'text-muted-foreground line-through' : ''}`}
                            title={metricName}
                          >
                            {metricName}
                          </span>
                          <ChevronDown className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        </div>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start">
                        <DropdownMenuItem 
                          onClick={() => showOnlyMetric(metricName)}
                          data-testid={`menu-only-metric-${metricName}`}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          Show Only This
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          onClick={() => setFullscreenMetric(metricName)}
                          disabled={hiddenMetrics.has(metricName)}
                          data-testid={`menu-expand-metric-${metricName}`}
                        >
                          <Maximize2 className="w-4 h-4 mr-2" />
                          Expand
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={() => resetDomain(metricName)}
                          disabled={!metricDomains[metricName]}
                          data-testid={`menu-reset-zoom-metric-${metricName}`}
                        >
                          <RotateCcw className="w-4 h-4 mr-2" />
                          Reset Zoom
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          <Separator />

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label className="text-sm font-medium">Zoom</Label>
              {Object.values(metricDomains).some(d => d?.x || d?.y) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={resetAllDomains}
                  data-testid="button-reset-all-zoom"
                >
                  Reset All
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Drag on chart to zoom. Double-click to reset. Use toolbar for pan/zoom modes.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex-1 overflow-auto">
        <div className="mb-4">
            <PageHeader
            title="Scalars"
              description={`Scalars visualization for "${project?.name}" - ${visibleExperiments.length} experiments visible`}
              actions={pageActions}
          />
        </div>

        {visibleMetrics.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No scalars visible"
            description="All scalars are hidden. Click 'Show All' to display them."
          />
        ) : (
          <div
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(auto-fill, ${cardMinWidth}px)`,
              justifyContent: "start",
            }}
          >
            {visibleMetrics.map((metric) => {
              const data = chartDataByMetric[metric.name] || [];
              const hasData = data.length > 0;
              const domain = metricDomains[metric.name] || { x: null, y: null };

              return (
                <Card key={metric.name} data-testid={`card-metric-${metric.name}`}>
                  <CardHeader className="py-2 px-3">
                    <CardTitle className="text-sm flex items-center justify-between gap-2">
                      <span className="truncate">{metric.name}</span>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {domain && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => resetDomain(metric.name)}
                            title="Reset zoom"
                            data-testid={`button-reset-zoom-${metric.name}`}
                          >
                            <RotateCcw className="w-3 h-3" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => setFullscreenMetric(metric.name)}
                          title="Expand"
                          data-testid={`button-expand-${metric.name}`}
                        >
                          <Maximize2 className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => toggleMetric(metric.name)}
                          title="Hide"
                          data-testid={`button-hide-metric-${metric.name}`}
                        >
                          <EyeOff className="w-3 h-3" />
                        </Button>
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-2 pb-2 pt-0">
                    {!hasData ? (
                      <div
                        className="flex items-center justify-center text-sm text-muted-foreground"
                        style={{ height: cardHeight }}
                      >
                        No data for selected experiments
                      </div>
                    ) : (
                      <MetricChart
                        metricName={metric.name}
                        data={data}
                        experiments={experiments}
                        selectedExperiments={visibleExperiments}
                        allExperiments={experiments}
                        height={cardHeight}
                        showBrush={true}
                        domain={domain}
                        onDomainChange={(d) => handleDomainChange(metric.name, d)}
                        onExpand={() => setFullscreenMetric(metric.name)}
                        onReset={() => resetDomain(metric.name)}
                      />
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {viewsSidebarOpen && (
        <ScalarViewsSidebar
          projectId={projectId}
          currentQuery={currentQueryString}
          onRestoreView={handleRestoreSavedView}
          onClose={() => setViewsSidebarOpen(false)}
        />
      )}

      <Dialog open={!!fullscreenMetric} onOpenChange={(open) => !open && setFullscreenMetric(null)}>
        <DialogContent className="max-w-6xl w-[90vw] h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between gap-4">
              <span>{fullscreenMetric}</span>
              <div className="flex items-center gap-2">
                {fullscreenMetric && (metricDomains[fullscreenMetric]?.x || metricDomains[fullscreenMetric]?.y) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fullscreenMetric && resetDomain(fullscreenMetric)}
                    data-testid="button-reset-zoom-fullscreen"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset Zoom
                  </Button>
                )}
              </div>
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            {fullscreenMetric && (
              <MetricChart
                metricName={fullscreenMetric}
                data={fullscreenMetricData}
                experiments={experiments}
                selectedExperiments={visibleExperiments}
                allExperiments={experiments}
                height={500}
                showBrush={true}
                domain={metricDomains[fullscreenMetric] || { x: null, y: null }}
                onDomainChange={(d) => handleDomainChange(fullscreenMetric, d)}
                isFullscreen={true}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!editExperiment}
        onOpenChange={(open) => !open && setEditExperiment(null)}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Experiment</DialogTitle>
          </DialogHeader>
          {editExperiment && (
            <ExperimentEditForm
              experiment={editExperiment}
              isSaving={updateExperiment.isPending}
              onSave={(data) => {
                updateExperiment.mutate(
                  {
                    id: editExperiment.id,
                    data: {
                      name: data.name,
                      description: data.description,
                      color: data.color,
                    },
                  },
                  {
                    onSuccess: () => setEditExperiment(null),
                  }
                );
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

