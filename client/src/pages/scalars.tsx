import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearch, useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
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
import { useProjectId } from "@/hooks/use-project-id";
import { AlertCircle, BarChart3, ChevronDown, Eye, EyeOff, Maximize2, RotateCcw } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
  ReferenceArea,
} from "recharts";
import type { Project, Experiment, Metric } from "@shared/schema";

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
  domain?: [number, number] | null;
  onDomainChange?: (domain: [number, number] | null) => void;
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
  showBrush = true,
  domain,
  onDomainChange,
  onExpand,
  onReset,
  isFullscreen = false,
}: MetricChartProps) {
  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);

  const handleMouseDown = (e: any) => {
    if (e && e.activeLabel !== undefined) {
      setRefAreaLeft(e.activeLabel);
      setIsSelecting(true);
    }
  };

  const handleMouseMove = (e: any) => {
    if (isSelecting && e && e.activeLabel !== undefined) {
      setRefAreaRight(e.activeLabel);
    }
  };

  const handleMouseUp = () => {
    if (refAreaLeft !== null && refAreaRight !== null && refAreaLeft !== refAreaRight) {
      const left = Math.min(refAreaLeft, refAreaRight);
      const right = Math.max(refAreaLeft, refAreaRight);
      onDomainChange?.([left, right]);
    }
    setRefAreaLeft(null);
    setRefAreaRight(null);
    setIsSelecting(false);
  };

  const handleBrushChange = useCallback((brushData: any) => {
    if (brushData && brushData.startIndex !== undefined && brushData.endIndex !== undefined) {
      const startStep = data[brushData.startIndex]?.step as number;
      const endStep = data[brushData.endIndex]?.step as number;
      if (startStep !== undefined && endStep !== undefined) {
        onDomainChange?.([startStep, endStep]);
      }
    }
  }, [data, onDomainChange]);

  const brushStartIndex = useMemo(() => {
    if (!domain || data.length === 0) return 0;
    const idx = data.findIndex(d => (d.step as number) >= domain[0]);
    return idx >= 0 ? idx : 0;
  }, [data, domain]);

  const brushEndIndex = useMemo(() => {
    if (!domain || data.length === 0) return Math.max(0, data.length - 1);
    for (let i = data.length - 1; i >= 0; i--) {
      if ((data[i].step as number) <= domain[1]) return i;
    }
    return data.length - 1;
  }, [data, domain]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data for selected experiments
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="step"
            tick={{ fontSize: isFullscreen ? 12 : 10 }}
            tickLine={false}
            domain={domain || ['auto', 'auto']}
            allowDataOverflow={!!domain}
            type="number"
          />
          <YAxis
            tick={{ fontSize: isFullscreen ? 12 : 10 }}
            tickLine={false}
            width={isFullscreen ? 60 : 50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "var(--radius)",
              fontSize: isFullscreen ? 14 : 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: isFullscreen ? 12 : 10 }} />
          {selectedExperiments.map((experiment) => {
            const originalIndex = allExperiments.findIndex(e => e.id === experiment.id);
            return (
              <Line
                key={experiment.id}
                type="monotone"
                dataKey={experiment.name}
                stroke={CHART_COLORS[originalIndex % CHART_COLORS.length]}
                strokeWidth={isFullscreen ? 2 : 1.5}
                dot={false}
                activeDot={{ r: isFullscreen ? 5 : 3 }}
              />
            );
          })}
          {refAreaLeft !== null && refAreaRight !== null && (
            <ReferenceArea
              x1={refAreaLeft}
              x2={refAreaRight}
              strokeOpacity={0.3}
              fill="hsl(var(--primary))"
              fillOpacity={0.1}
            />
          )}
          {showBrush && data.length > 10 && (
            <Brush
              dataKey="step"
              height={20}
              stroke="hsl(var(--muted-foreground))"
              fill="hsl(var(--muted))"
              startIndex={brushStartIndex}
              endIndex={brushEndIndex}
              onChange={handleBrushChange}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Scalars() {
  const projectId = useProjectId();
  const searchString = useSearch();
  const [, navigate] = useLocation();
  
  const [smoothing, setSmoothing] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const [selectedExperimentIndices, setSelectedExperimentIndices] = useState<Set<number>>(new Set());
  const [hiddenMetrics, setHiddenMetrics] = useState<Set<string>>(new Set());
  const [metricDomains, setMetricDomains] = useState<Record<string, [number, number] | null>>({});
  const [fullscreenMetric, setFullscreenMetric] = useState<string | null>(null);

  const { data: project } = useQuery<Project>({
    queryKey: ["/api/projects", projectId],
    enabled: !!projectId,
  });

  const { data: experiments = [], isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/projects", projectId, "experiments"],
    enabled: !!projectId,
  });

  const { data: allMetrics = {}, isLoading: metricsLoading } = useQuery<Record<string, Metric[]>>({
    queryKey: ["/api/projects", projectId, "all-metrics"],
    enabled: !!projectId,
  });

  useEffect(() => {
    if (experiments.length === 0 || !project?.metrics || initialized) return;
    
    const params = new URLSearchParams(searchString);
    const expParam = params.get("exp");
    const metParam = params.get("met");
    const smoothParam = params.get("s");
    
    if (expParam) {
      const indices = decodeSelection(expParam);
      setSelectedExperimentIndices(new Set(indices.filter(i => i >= 0 && i < experiments.length)));
    } else {
      setSelectedExperimentIndices(new Set(experiments.map((_, i) => i)));
    }
    
    if (metParam) {
      const hiddenIndices = decodeSelection(metParam);
      const metricNames = project.metrics.map(m => m.name);
      setHiddenMetrics(new Set(hiddenIndices.map(i => metricNames[i]).filter(Boolean)));
    }
    
    if (smoothParam) {
      const s = parseFloat(smoothParam);
      if (!isNaN(s) && s >= 0 && s <= 1) {
        setSmoothing(s);
      }
    }
    
    setInitialized(true);
  }, [experiments, searchString, initialized, project]);

  const updateUrl = useCallback((expIndices: Set<number>, hiddenMets: Set<string>, smooth: number) => {
    const params = new URLSearchParams();
    
    const allSelected = expIndices.size === experiments.length;
    if (!allSelected && expIndices.size > 0) {
      params.set("exp", encodeSelection(Array.from(expIndices).sort()));
    }
    
    if (hiddenMets.size > 0) {
      const metricNames = project?.metrics?.map(m => m.name) || [];
      const hiddenIndices = Array.from(hiddenMets)
        .map(name => metricNames.indexOf(name))
        .filter(i => i >= 0)
        .sort();
      if (hiddenIndices.length > 0) {
        params.set("met", encodeSelection(hiddenIndices));
      }
    }
    
    if (smooth > 0) {
      params.set("s", smooth.toFixed(2));
    }
    
    const queryString = params.toString();
    const basePath = `/projects/${projectId}/scalars`;
    navigate(queryString ? `${basePath}?${queryString}` : basePath, { replace: true });
  }, [experiments.length, project, projectId, navigate]);

  const toggleExperiment = (index: number) => {
    setSelectedExperimentIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      updateUrl(next, hiddenMetrics, smoothing);
      return next;
    });
  };

  const selectAllExperiments = () => {
    const all = new Set(experiments.map((_, i) => i));
    setSelectedExperimentIndices(all);
    updateUrl(all, hiddenMetrics, smoothing);
  };

  const clearAllExperiments = () => {
    setSelectedExperimentIndices(new Set());
    updateUrl(new Set(), hiddenMetrics, smoothing);
  };

  const toggleMetric = (metricName: string) => {
    setHiddenMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(metricName)) {
        next.delete(metricName);
      } else {
        next.add(metricName);
      }
      updateUrl(selectedExperimentIndices, next, smoothing);
      return next;
    });
  };

  const showAllMetrics = () => {
    setHiddenMetrics(new Set());
    updateUrl(selectedExperimentIndices, new Set(), smoothing);
  };

  const showOnlyMetric = (metricName: string) => {
    if (!project?.metrics) return;
    const newHidden = new Set(project.metrics.map(m => m.name).filter(name => name !== metricName));
    setHiddenMetrics(newHidden);
    updateUrl(selectedExperimentIndices, newHidden, smoothing);
  };

  const handleSmoothingChange = (value: number[]) => {
    setSmoothing(value[0]);
  };

  const handleSmoothingCommit = (value: number[]) => {
    updateUrl(selectedExperimentIndices, hiddenMetrics, value[0]);
  };

  const handleDomainChange = (metricName: string, domain: [number, number] | null) => {
    setMetricDomains(prev => ({ ...prev, [metricName]: domain }));
  };

  const resetDomain = (metricName: string) => {
    setMetricDomains(prev => ({ ...prev, [metricName]: null }));
  };

  const resetAllDomains = () => {
    setMetricDomains({});
  };

  const visibleMetrics = useMemo(() => {
    if (!project?.metrics) return [];
    return project.metrics.filter(m => !hiddenMetrics.has(m.name));
  }, [project, hiddenMetrics]);

  const selectedExperiments = useMemo(() => {
    return experiments.filter((_, i) => selectedExperimentIndices.has(i));
  }, [experiments, selectedExperimentIndices]);

  const chartDataByMetric = useMemo(() => {
    const result: Record<string, Array<Record<string, number | null>>> = {};
    
    if (!allMetrics || selectedExperiments.length === 0) return result;

    for (const metric of visibleMetrics) {
      const stepMap = new Map<number, Record<string, number | null>>();
      const rawDataByExp: Record<string, { steps: number[]; values: number[] }> = {};
      
      selectedExperiments.forEach((experiment) => {
        const expMetrics = allMetrics[experiment.id] || [];
        const metricData = expMetrics
          .filter(m => m.name === metric.name)
          .sort((a, b) => a.step - b.step);
        
        if (metricData.length > 0) {
          rawDataByExp[experiment.id] = {
            steps: metricData.map(m => m.step),
            values: metricData.map(m => m.value),
          };
        }
      });

      Object.entries(rawDataByExp).forEach(([expId, data]) => {
        const experiment = experiments.find(e => e.id === expId);
        if (!experiment) return;
        
        const smoothedValues = applySmoothing(data.values, smoothing);
        
        data.steps.forEach((step, i) => {
          const existing = stepMap.get(step) || { step };
          existing[experiment.name] = smoothedValues[i];
          stepMap.set(step, existing);
        });
      });

      result[metric.name] = Array.from(stepMap.values()).sort(
        (a, b) => (a.step as number) - (b.step as number)
      );
    }

    return result;
  }, [allMetrics, selectedExperiments, experiments, visibleMetrics, smoothing]);

  const fullscreenMetricData = fullscreenMetric ? chartDataByMetric[fullscreenMetric] || [] : [];

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

  if (experimentsLoading || metricsLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Scalars"
          description="Compare metrics across experiments"
        />
        <ListSkeleton count={3} />
      </div>
    );
  }

  const gridCols = visibleMetrics.length === 1 ? 1 : visibleMetrics.length === 2 ? 2 : 
    visibleMetrics.length <= 4 ? 2 : 3;

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-4">
      <Card className="w-72 flex-shrink-0 flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Controls</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col gap-4">
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
                    <Checkbox
                      id={`exp-${index}`}
                      checked={selectedExperimentIndices.has(index)}
                      onCheckedChange={() => toggleExperiment(index)}
                      data-testid={`checkbox-experiment-${index}`}
                    />
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                    <label
                      htmlFor={`exp-${index}`}
                      className="text-sm truncate cursor-pointer flex-1"
                      title={experiment.name}
                    >
                      {experiment.name}
                    </label>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          <Separator />

          <div className="space-y-2 flex-1 min-h-0">
            <div className="flex items-center justify-between gap-2">
              <Label className="text-sm font-medium">Metrics</Label>
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
                {project?.metrics?.map((metric) => (
                  <DropdownMenu key={metric.name}>
                    <DropdownMenuTrigger asChild>
                      <div
                        className="flex items-center gap-2 py-1 px-1 rounded-md cursor-pointer hover-elevate"
                        data-testid={`dropdown-metric-${metric.name}`}
                      >
                        {hiddenMetrics.has(metric.name) ? (
                          <EyeOff className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        ) : (
                          <Eye className="w-3 h-3 flex-shrink-0" />
                        )}
                        <span 
                          className={`text-sm truncate flex-1 ${hiddenMetrics.has(metric.name) ? 'text-muted-foreground line-through' : ''}`}
                          title={metric.name}
                        >
                          {metric.name}
                        </span>
                        <ChevronDown className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                      </div>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                      <DropdownMenuItem 
                        onClick={() => toggleMetric(metric.name)}
                        data-testid={`menu-toggle-metric-${metric.name}`}
                      >
                        {hiddenMetrics.has(metric.name) ? (
                          <>
                            <Eye className="w-4 h-4 mr-2" />
                            Show
                          </>
                        ) : (
                          <>
                            <EyeOff className="w-4 h-4 mr-2" />
                            Hide
                          </>
                        )}
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        onClick={() => showOnlyMetric(metric.name)}
                        data-testid={`menu-only-metric-${metric.name}`}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        Show Only This
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem 
                        onClick={() => setFullscreenMetric(metric.name)}
                        disabled={hiddenMetrics.has(metric.name)}
                        data-testid={`menu-expand-metric-${metric.name}`}
                      >
                        <Maximize2 className="w-4 h-4 mr-2" />
                        Expand
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        onClick={() => resetDomain(metric.name)}
                        disabled={!metricDomains[metric.name]}
                        data-testid={`menu-reset-zoom-metric-${metric.name}`}
                      >
                        <RotateCcw className="w-4 h-4 mr-2" />
                        Reset Zoom
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ))}
              </div>
            </ScrollArea>
          </div>

          <Separator />

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label className="text-sm font-medium">Zoom</Label>
              {Object.values(metricDomains).some(d => d !== null) && (
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
              Drag on chart to zoom. Use brush below chart to pan.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex-1 overflow-auto">
        <div className="mb-4">
          <PageHeader
            title="Scalars"
            description={`Metrics visualization for "${project?.name}" - ${selectedExperiments.length} experiments selected`}
          />
        </div>

        {selectedExperiments.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="Select experiments"
            description="Choose one or more experiments from the sidebar to compare their metrics."
          />
        ) : visibleMetrics.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No metrics visible"
            description="All metrics are hidden. Click 'Show All' to display them."
          />
        ) : (
          <div 
            className="grid gap-4" 
            style={{ gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))` }}
          >
            {visibleMetrics.map((metric) => {
              const data = chartDataByMetric[metric.name] || [];
              const hasData = data.length > 0;
              const domain = metricDomains[metric.name] || null;

              return (
                <Card key={metric.name} data-testid={`card-metric-${metric.name}`}>
                  <CardHeader className="pb-2">
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
                  <CardContent>
                    {!hasData ? (
                      <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
                        No data for selected experiments
                      </div>
                    ) : (
                      <MetricChart
                        metricName={metric.name}
                        data={data}
                        experiments={experiments}
                        selectedExperiments={selectedExperiments}
                        allExperiments={experiments}
                        height={200}
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

      <Dialog open={!!fullscreenMetric} onOpenChange={(open) => !open && setFullscreenMetric(null)}>
        <DialogContent className="max-w-6xl w-[90vw] h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between gap-4">
              <span>{fullscreenMetric}</span>
              <div className="flex items-center gap-2">
                {fullscreenMetric && metricDomains[fullscreenMetric] && (
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
                selectedExperiments={selectedExperiments}
                allExperiments={experiments}
                height={500}
                showBrush={true}
                domain={metricDomains[fullscreenMetric] || null}
                onDomainChange={(d) => handleDomainChange(fullscreenMetric, d)}
                isFullscreen={true}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
