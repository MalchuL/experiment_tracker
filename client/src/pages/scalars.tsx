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
import { useProjectId } from "@/hooks/use-project-id";
import { AlertCircle, BarChart3, Eye, EyeOff } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
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

export default function Scalars() {
  const projectId = useProjectId();
  const searchString = useSearch();
  const [, navigate] = useLocation();
  
  const [smoothing, setSmoothing] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const [selectedExperimentIndices, setSelectedExperimentIndices] = useState<Set<number>>(new Set());
  const [hiddenMetrics, setHiddenMetrics] = useState<Set<string>>(new Set());

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

  const handleSmoothingChange = (value: number[]) => {
    const newSmoothing = value[0];
    setSmoothing(newSmoothing);
    updateUrl(selectedExperimentIndices, hiddenMetrics, newSmoothing);
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
                  <div
                    key={metric.name}
                    className="flex items-center gap-2 py-1"
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => toggleMetric(metric.name)}
                      data-testid={`button-toggle-metric-${metric.name}`}
                    >
                      {hiddenMetrics.has(metric.name) ? (
                        <EyeOff className="w-3 h-3 text-muted-foreground" />
                      ) : (
                        <Eye className="w-3 h-3" />
                      )}
                    </Button>
                    <span 
                      className={`text-sm truncate flex-1 ${hiddenMetrics.has(metric.name) ? 'text-muted-foreground line-through' : ''}`}
                      title={metric.name}
                    >
                      {metric.name}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
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

              return (
                <Card key={metric.name} data-testid={`card-metric-${metric.name}`}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between gap-2">
                      <span className="truncate">{metric.name}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 flex-shrink-0"
                        onClick={() => toggleMetric(metric.name)}
                        data-testid={`button-hide-metric-${metric.name}`}
                      >
                        <EyeOff className="w-3 h-3" />
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {!hasData ? (
                      <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
                        No data for selected experiments
                      </div>
                    ) : (
                      <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                            <XAxis
                              dataKey="step"
                              tick={{ fontSize: 10 }}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fontSize: 10 }}
                              tickLine={false}
                              width={50}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(var(--card))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "var(--radius)",
                                fontSize: 12,
                              }}
                            />
                            <Legend wrapperStyle={{ fontSize: 10 }} />
                            {selectedExperiments.map((experiment) => {
                              const originalIndex = experiments.findIndex(e => e.id === experiment.id);
                              return (
                                <Line
                                  key={experiment.id}
                                  type="monotone"
                                  dataKey={experiment.name}
                                  stroke={CHART_COLORS[originalIndex % CHART_COLORS.length]}
                                  strokeWidth={1.5}
                                  dot={false}
                                  activeDot={{ r: 3 }}
                                />
                              );
                            })}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
