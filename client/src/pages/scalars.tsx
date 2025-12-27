import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { ListSkeleton } from "@/components/loading-skeleton";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useExperimentStore } from "@/stores/experiment-store";
import { TrendingUp, TrendingDown, AlertCircle, BarChart3 } from "lucide-react";
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
];

export default function Scalars() {
  const { selectedProjectId } = useExperimentStore();
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);
  const [selectedExperiments, setSelectedExperiments] = useState<Set<string>>(new Set());

  const { data: project } = useQuery<Project>({
    queryKey: ["/api/projects", selectedProjectId],
    enabled: !!selectedProjectId,
  });

  const { data: experiments = [], isLoading: experimentsLoading } = useQuery<Experiment[]>({
    queryKey: ["/api/projects", selectedProjectId, "experiments"],
    enabled: !!selectedProjectId,
  });

  const { data: allMetrics = [], isLoading: metricsLoading } = useQuery<Record<string, Metric[]>>({
    queryKey: ["/api/projects", selectedProjectId, "all-metrics"],
    enabled: !!selectedProjectId,
  });

  const availableMetricNames = useMemo(() => {
    if (!project?.metrics) return [];
    return project.metrics.map((m) => m.name);
  }, [project]);

  const chartData = useMemo(() => {
    if (!selectedMetric || !allMetrics || selectedExperiments.size === 0) return [];

    const stepMap = new Map<number, Record<string, number | null>>();

    Object.entries(allMetrics).forEach(([experimentId, metrics]) => {
      if (!selectedExperiments.has(experimentId)) return;
      const experiment = experiments.find((e) => e.id === experimentId);
      if (!experiment) return;

      metrics
        .filter((m) => m.name === selectedMetric)
        .forEach((metric) => {
          const existing = stepMap.get(metric.step) || { step: metric.step };
          existing[experiment.name] = metric.value;
          stepMap.set(metric.step, existing);
        });
    });

    return Array.from(stepMap.values()).sort((a, b) => (a.step as number) - (b.step as number));
  }, [selectedMetric, allMetrics, selectedExperiments, experiments]);

  const toggleExperiment = (experimentId: string) => {
    setSelectedExperiments((prev) => {
      const next = new Set(prev);
      if (next.has(experimentId)) {
        next.delete(experimentId);
      } else {
        next.add(experimentId);
      }
      return next;
    });
  };

  const selectAllExperiments = () => {
    setSelectedExperiments(new Set(experiments.map((e) => e.id)));
  };

  const clearAllExperiments = () => {
    setSelectedExperiments(new Set());
  };

  if (!selectedProjectId) {
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

  const selectedMetricConfig = project?.metrics.find((m) => m.name === selectedMetric);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scalars"
        description={`Metrics visualization for "${project?.name}"`}
      />

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Metric</Label>
              <Select
                value={selectedMetric || ""}
                onValueChange={(v) => setSelectedMetric(v || null)}
              >
                <SelectTrigger data-testid="select-metric">
                  <SelectValue placeholder="Select metric" />
                </SelectTrigger>
                <SelectContent>
                  {availableMetricNames.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedMetricConfig && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  {selectedMetricConfig.direction === "maximize" ? (
                    <>
                      <TrendingUp className="w-3 h-3" />
                      Higher is better
                    </>
                  ) : (
                    <>
                      <TrendingDown className="w-3 h-3" />
                      Lower is better
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Experiments</Label>
                <div className="flex gap-1">
                  <button
                    className="text-xs text-muted-foreground hover:text-foreground"
                    onClick={selectAllExperiments}
                    data-testid="button-select-all"
                  >
                    All
                  </button>
                  <span className="text-xs text-muted-foreground">/</span>
                  <button
                    className="text-xs text-muted-foreground hover:text-foreground"
                    onClick={clearAllExperiments}
                    data-testid="button-clear-all"
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {experiments.map((experiment, index) => (
                  <div
                    key={experiment.id}
                    className="flex items-center gap-2"
                  >
                    <Checkbox
                      id={`exp-${experiment.id}`}
                      checked={selectedExperiments.has(experiment.id)}
                      onCheckedChange={() => toggleExperiment(experiment.id)}
                      data-testid={`checkbox-experiment-${experiment.id}`}
                    />
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                    <label
                      htmlFor={`exp-${experiment.id}`}
                      className="text-sm truncate cursor-pointer"
                    >
                      {experiment.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              {selectedMetric || "Metric"} over Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedMetric ? (
              <EmptyState
                icon={BarChart3}
                title="Select a metric"
                description="Choose a metric from the dropdown to visualize experiment results."
              />
            ) : selectedExperiments.size === 0 ? (
              <EmptyState
                icon={BarChart3}
                title="Select experiments"
                description="Choose one or more experiments to compare their metrics."
              />
            ) : chartData.length === 0 ? (
              <EmptyState
                icon={BarChart3}
                title="No data available"
                description="The selected experiments have no logged metrics for this metric."
              />
            ) : (
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="step"
                      label={{ value: "Step", position: "insideBottomRight", offset: -5 }}
                      className="text-xs"
                    />
                    <YAxis
                      label={{
                        value: selectedMetric,
                        angle: -90,
                        position: "insideLeft",
                      }}
                      className="text-xs"
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "var(--radius)",
                      }}
                    />
                    <Legend />
                    {experiments
                      .filter((e) => selectedExperiments.has(e.id))
                      .map((experiment, index) => (
                        <Line
                          key={experiment.id}
                          type="monotone"
                          dataKey={experiment.name}
                          stroke={CHART_COLORS[experiments.findIndex((e) => e.id === experiment.id) % CHART_COLORS.length]}
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                        />
                      ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedMetric && selectedExperiments.size > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {experiments
                .filter((e) => selectedExperiments.has(e.id))
                .map((experiment, index) => {
                  const expMetrics = allMetrics[experiment.id] || [];
                  const metricValues = expMetrics
                    .filter((m) => m.name === selectedMetric)
                    .map((m) => m.value);

                  if (metricValues.length === 0) return null;

                  const best =
                    selectedMetricConfig?.direction === "minimize"
                      ? Math.min(...metricValues)
                      : Math.max(...metricValues);
                  const latest = metricValues[metricValues.length - 1];

                  return (
                    <div
                      key={experiment.id}
                      className="p-3 rounded-md border"
                      data-testid={`summary-${experiment.id}`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor:
                              CHART_COLORS[
                                experiments.findIndex((e) => e.id === experiment.id) %
                                  CHART_COLORS.length
                              ],
                          }}
                        />
                        <span className="text-sm font-medium truncate">
                          {experiment.name}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <p className="text-xs text-muted-foreground">Best</p>
                          <p className="font-mono">{best.toFixed(4)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Latest</p>
                          <p className="font-mono">{latest.toFixed(4)}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
