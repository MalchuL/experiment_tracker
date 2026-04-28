"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { type Project, type ProjectDisplayMetric } from "../../types";
import { Eye, ChevronDown, Check, TrendingUp, TrendingDown } from "lucide-react";
import {
  formatMetricLabel,
  isExplicitlyInDisplayList,
  removeFromDisplayList,
  projectMetricKeyString,
  trackedToDisplayKey,
} from "@/lib/metrics/format-metric-label";

interface DisplayMetricsFormProps {
  project: Project;
  onSubmit: (displayMetrics: ProjectDisplayMetric[]) => void;
  isPending: boolean;
}

export function DisplayMetricsForm({ project, onSubmit, isPending }: DisplayMetricsFormProps) {
  const persistedDisplayMetrics = useMemo(
    () => project.metrics.displayMetrics,
    [project.metrics]
  );

  const [displayMetrics, setDisplayMetrics] = useState<ProjectDisplayMetric[]>(persistedDisplayMetrics);

  useEffect(() => {
    setDisplayMetrics(persistedDisplayMetrics);
  }, [persistedDisplayMetrics]);

  if (project.metrics.trackedMetrics.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No metrics configured. Add metrics below first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-full justify-between" data-testid="dropdown-display-metrics">
            <span className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              {displayMetrics.length === 0
                ? `0 of ${project.metrics.trackedMetrics.length} metrics selected`
                : displayMetrics.length === project.metrics.trackedMetrics.length
                  ? "All metrics selected"
                  : `${displayMetrics.length} of ${project.metrics.trackedMetrics.length} metrics selected`}
            </span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-64">
          <DropdownMenuItem
            onClick={() => {
              setDisplayMetrics(project.metrics.trackedMetrics.map(trackedToDisplayKey));
            }}
            data-testid="menu-select-all-metrics"
          >
            <Check className="h-4 w-4 mr-2" />
            Select All
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              setDisplayMetrics([]);
            }}
            data-testid="menu-clear-all-metrics"
          >
            Clear All
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          {project.metrics.trackedMetrics.map((metric) => {
            const checked = isExplicitlyInDisplayList(
              { name: metric.name, label: metric.label },
              displayMetrics
            );
            return (
              <DropdownMenuCheckboxItem
                key={projectMetricKeyString(metric)}
                checked={checked}
                onCheckedChange={(next) => {
                  if (next) {
                    const key = trackedToDisplayKey(metric);
                    if (!isExplicitlyInDisplayList({ name: metric.name, label: metric.label }, displayMetrics)) {
                      setDisplayMetrics((prev) => [...prev, key]);
                    }
                  } else {
                    setDisplayMetrics((prev) => removeFromDisplayList(prev, metric));
                  }
                }}
                data-testid={`menu-metric-${projectMetricKeyString(metric).replace(/[^a-zA-Z0-9-_]/g, "-")}`}
              >
                <span className="flex items-center gap-2">
                  {formatMetricLabel(metric.name, metric.label ?? null)}
                  {metric.direction === "maximize" ? (
                    <TrendingUp className="h-3 w-3 text-green-500" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-green-500" />
                  )}
                </span>
              </DropdownMenuCheckboxItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {displayMetrics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {displayMetrics.map((entry) => {
            const label =
              typeof entry === "string" ? entry : formatMetricLabel(entry.name, entry.label ?? null);
            return (
              <Badge key={typeof entry === "string" ? entry : projectMetricKeyString(entry)} variant="secondary" className="text-xs">
                {label}
              </Badge>
            );
          })}
        </div>
      )}

      <Button
        type="button"
        onClick={() => onSubmit(displayMetrics)}
        disabled={isPending}
        className="w-full"
        data-testid="button-save-display-metrics"
      >
        Save Display Settings
      </Button>
    </div>
  );
}
