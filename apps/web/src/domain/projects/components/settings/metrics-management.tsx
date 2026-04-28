"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Project, ProjectMetric } from "../../types";
import { Plus, Trash2, TrendingUp, TrendingDown } from "lucide-react";
import { useToast } from "@/lib/hooks/use-toast";
import { projectsService } from "@/domain/projects/services";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import {
  displayMetricKeyEquals,
  formatMetricLabel,
  projectMetricKeyString,
} from "@/lib/metrics/format-metric-label";

interface MetricsManagementProps {
  project: Project;
  projectId: string;
  onAddMetric: (metric: ProjectMetric) => void;
  onRemoveMetric: (metric: ProjectMetric) => void;
  onUpdateMetricDirection: (metric: ProjectMetric, direction: "maximize" | "minimize") => void;
  isPending: boolean;
}

export function MetricsManagement({
  project,
  projectId,
  onAddMetric,
  onRemoveMetric,
  onUpdateMetricDirection,
  isPending,
}: MetricsManagementProps) {
  const [newMetricName, setNewMetricName] = useState("");
  const [newMetricLabel, setNewMetricLabel] = useState("");
  const [newMetricDirection, setNewMetricDirection] = useState<"maximize" | "minimize">("maximize");
  const [metricPopoverOpen, setMetricPopoverOpen] = useState(false);
  const { toast } = useToast();

  const { data: uniqueDimensions } = useQuery({
    queryKey: [QUERY_KEYS.METRICS.UNIQUE_DIMENSIONS(projectId)],
    queryFn: () => projectsService.getUniqueMetricDimensions(projectId),
    enabled: metricPopoverOpen,
    staleTime: 5 * 60 * 1000,
  });

  const isDuplicate = (name: string, label: string | null) =>
    project.metrics.trackedMetrics.some((m) =>
      displayMetricKeyEquals({ name: m.name, label: m.label }, { name, label })
    );

  const handleAddMetric = () => {
    if (!newMetricName.trim() || !project) return;
    const name = newMetricName.trim();
    const label = newMetricLabel.trim() ? newMetricLabel.trim() : null;
    if (isDuplicate(name, label)) {
      toast({
        title: "Metric already tracked",
        description: `You are already tracking ${formatMetricLabel(name, label)}.`,
        variant: "destructive",
      });
      return;
    }

    const newMetric: ProjectMetric = {
      name,
      label,
      direction: newMetricDirection,
      aggregation: "best",
    };

    onAddMetric(newMetric);
    setNewMetricName("");
    setNewMetricLabel("");
    setMetricPopoverOpen(false);
  };

  const searchLower = `${newMetricName} ${newMetricLabel}`.toLowerCase();
  const dimensionItems = uniqueDimensions?.items ?? [];
  const suggested = dimensionItems.filter((dim) => {
    if (isDuplicate(dim.name, dim.label)) {
      return false;
    }
    const label = formatMetricLabel(dim.name, dim.label);
    return !searchLower.trim() || label.toLowerCase().includes(searchLower.trim());
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-start">
        <Popover open={metricPopoverOpen} onOpenChange={setMetricPopoverOpen}>
          <PopoverTrigger asChild>
            <div className="flex-1 min-w-[200px] relative">
              <Input
                placeholder="Metric name (e.g. loss)"
                value={newMetricName}
                onChange={(e) => {
                  setNewMetricName(e.target.value);
                  if (e.target.value.length > 0) {
                    setMetricPopoverOpen(true);
                  }
                }}
                onFocus={() => {
                  setMetricPopoverOpen(true);
                }}
                className="w-full"
                data-testid="input-new-metric"
              />
            </div>
          </PopoverTrigger>
          <PopoverContent
            className="p-0 w-[min(100vw-2rem,320px)]"
            align="start"
            onOpenAutoFocus={(e) => e.preventDefault()}
          >
            <div className="max-h-64 overflow-y-auto p-2 text-sm">
              {suggested.length > 0 ? (
                <div className="space-y-0.5" role="list">
                  <p className="px-2 py-1 text-xs font-medium text-muted-foreground">Observed in project</p>
                  {suggested.slice(0, 20).map((dim) => (
                    <button
                      key={`${dim.name}::${dim.label ?? ""}`}
                      type="button"
                      role="listitem"
                      className="w-full text-left rounded-sm px-2 py-1.5 hover:bg-accent"
                      onClick={() => {
                        setNewMetricName(dim.name);
                        setNewMetricLabel(dim.label ?? "");
                        setMetricPopoverOpen(false);
                      }}
                    >
                      {formatMetricLabel(dim.name, dim.label)}
                    </button>
                  ))}
                </div>
              ) : newMetricName.trim() ? (
                <p className="p-2 text-muted-foreground">
                  No matches. Press Add to track &quot;
                  {formatMetricLabel(newMetricName.trim(), newMetricLabel.trim() || null)}&quot;.
                </p>
              ) : (
                <p className="p-2 text-muted-foreground">
                  Type a metric name (and optional label), or open this list after logging metrics.
                </p>
              )}
            </div>
          </PopoverContent>
        </Popover>
        <Input
          className="w-[140px]"
          placeholder="Label (opt.)"
          value={newMetricLabel}
          onChange={(e) => setNewMetricLabel(e.target.value)}
          data-testid="input-new-metric-label"
        />
        <Select
          value={newMetricDirection}
          onValueChange={(v) => setNewMetricDirection(v as "maximize" | "minimize")}
        >
          <SelectTrigger className="w-[140px]" data-testid="select-metric-direction">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="maximize">Maximize</SelectItem>
            <SelectItem value="minimize">Minimize</SelectItem>
          </SelectContent>
        </Select>
        <Button
          onClick={handleAddMetric}
          disabled={!newMetricName.trim() || isPending}
          data-testid="button-add-metric"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-2">
        {project.metrics.trackedMetrics.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No metrics configured. Add metrics to track experiment performance.
          </p>
        ) : (
          project.metrics.trackedMetrics.map((metric) => (
            <div
              key={projectMetricKeyString(metric)}
              className="flex items-center justify-between gap-4 p-3 rounded-md border"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Badge variant="secondary" className="truncate max-w-[240px]">
                  {formatMetricLabel(metric.name, metric.label ?? null)}
                </Badge>
                {metric.direction === "maximize" ? (
                  <TrendingUp className="h-4 w-4 flex-shrink-0 text-green-500" />
                ) : (
                  <TrendingDown className="h-4 w-4 flex-shrink-0 text-red-500" />
                )}
              </div>
              <div className="flex items-center gap-2">
                <Select
                  value={metric.direction}
                  onValueChange={(v) => onUpdateMetricDirection(metric, v as "maximize" | "minimize")}
                  disabled={isPending}
                >
                  <SelectTrigger className="w-[120px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="maximize">Maximize</SelectItem>
                    <SelectItem value="minimize">Minimize</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => onRemoveMetric(metric)}
                  disabled={isPending}
                  data-testid={`button-remove-metric-${projectMetricKeyString(metric).replace(/[^a-zA-Z0-9-_]/g, "-")}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
