"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Form } from "@/components/ui/form";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { settingsSchema, type SettingsFormData } from "../../schemas/settings";
import { type Project } from "../../types";
import { Eye, ChevronDown, Check, TrendingUp, TrendingDown } from "lucide-react";
import {
  formatMetricLabel,
  isTrackedInDisplayList,
  removeFromDisplayList,
  projectMetricKeyString,
  trackedToDisplayKey,
} from "@/lib/metrics/format-metric-label";

interface DisplayMetricsFormProps {
  project: Project;
  onSubmit: (data: SettingsFormData) => void;
  isPending: boolean;
}

export function DisplayMetricsForm({ project, onSubmit, isPending }: DisplayMetricsFormProps) {
  const form = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      namingPattern: "{num}_from_{parent}_{change}",
      displayMetrics: project?.metrics?.displayMetrics || [],
    },
    values: {
      namingPattern: "{num}_from_{parent}_{change}",
      displayMetrics: project?.metrics?.displayMetrics || [],
    },
  });

  if (project.metrics.trackedMetrics.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No metrics configured. Add metrics below first.
      </p>
    );
  }

  return (
    <Form {...form}>
      <form className="space-y-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="w-full justify-between" data-testid="dropdown-display-metrics">
              <span className="flex items-center gap-2">
                <Eye className="h-4 w-4" />
                {form.watch("displayMetrics").length === 0
                  ? "Select metrics to display…"
                  : form.watch("displayMetrics").length === project.metrics.trackedMetrics.length
                  ? "All metrics selected"
                  : `${form.watch("displayMetrics").length} of ${project.metrics.trackedMetrics.length} metrics selected`}
              </span>
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-64">
            <DropdownMenuItem
              onClick={() => {
                form.setValue("displayMetrics", project.metrics.trackedMetrics.map(trackedToDisplayKey));
              }}
              data-testid="menu-select-all-metrics"
            >
              <Check className="h-4 w-4 mr-2" />
              Select All
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                form.setValue("displayMetrics", []);
              }}
              data-testid="menu-clear-all-metrics"
            >
              Clear All
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {project.metrics.trackedMetrics.map((metric) => {
              const checked = isTrackedInDisplayList(
                { name: metric.name, label: metric.label },
                form.watch("displayMetrics")
              );
              return (
                <DropdownMenuCheckboxItem
                  key={projectMetricKeyString(metric)}
                  checked={checked}
                  onCheckedChange={(next) => {
                    const current = form.getValues("displayMetrics");
                    if (next) {
                      const key = trackedToDisplayKey(metric);
                      if (!isTrackedInDisplayList({ name: metric.name, label: metric.label }, current)) {
                        form.setValue("displayMetrics", [...current, key]);
                      }
                    } else {
                      form.setValue("displayMetrics", removeFromDisplayList(current, metric));
                    }
                  }}
                  data-testid={`menu-metric-${projectMetricKeyString(metric).replace(/[^a-zA-Z0-9-_]/g, "-")}`}
                >
                  <span className="flex items-center gap-2">
                    {formatMetricLabel(metric.name, metric.label ?? null)}
                    {metric.direction === "maximize" ? (
                      <TrendingUp className="h-3 w-3 text-green-500" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-red-500" />
                    )}
                  </span>
                </DropdownMenuCheckboxItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>

        {form.watch("displayMetrics").length > 0 && (
          <div className="flex flex-wrap gap-1">
            {form.watch("displayMetrics").map((entry) => {
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
          onClick={form.handleSubmit(onSubmit)}
          disabled={isPending}
          className="w-full"
          data-testid="button-save-display-metrics"
        >
          Save Display Settings
        </Button>
      </form>
    </Form>
  );
}
