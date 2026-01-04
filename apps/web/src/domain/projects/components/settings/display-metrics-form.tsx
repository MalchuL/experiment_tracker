"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Form,
} from "@/components/ui/form";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { settingsSchema, SettingsFormData } from "../../schemas/settings";
import { Project } from "../../types";
import { Eye, ChevronDown, Check, TrendingUp, TrendingDown } from "lucide-react";

interface DisplayMetricsFormProps {
  project: Project;
  onSubmit: (data: SettingsFormData) => void;
  isPending: boolean;
}

export function DisplayMetricsForm({ project, onSubmit, isPending }: DisplayMetricsFormProps) {
  const form = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      namingPattern: project?.settings?.namingPattern || "{num}_from_{parent}_{change}",
      displayMetrics: project?.settings?.displayMetrics || [],
    },
    values: {
      namingPattern: project?.settings?.namingPattern || "{num}_from_{parent}_{change}",
      displayMetrics: project?.settings?.displayMetrics || [],
    },
  });

  if (project.metrics.length === 0) {
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
                <Eye className="w-4 h-4" />
                {form.watch("displayMetrics").length === 0
                  ? "Select metrics to display..."
                  : form.watch("displayMetrics").length === project.metrics.length
                  ? "All metrics selected"
                  : `${form.watch("displayMetrics").length} of ${project.metrics.length} metrics selected`}
              </span>
              <ChevronDown className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-64">
            <DropdownMenuItem
              onClick={() => {
                form.setValue("displayMetrics", project.metrics.map(m => m.name));
              }}
              data-testid="menu-select-all-metrics"
            >
              <Check className="w-4 h-4 mr-2" />
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
            {project.metrics.map((metric) => (
              <DropdownMenuCheckboxItem
                key={metric.name}
                checked={form.watch("displayMetrics").includes(metric.name)}
                onCheckedChange={(checked) => {
                  const current = form.getValues("displayMetrics");
                  if (checked) {
                    form.setValue("displayMetrics", [...current, metric.name]);
                  } else {
                    form.setValue("displayMetrics", current.filter(m => m !== metric.name));
                  }
                }}
                data-testid={`menu-metric-${metric.name}`}
              >
                <span className="flex items-center gap-2">
                  {metric.name}
                  {metric.direction === "maximize" ? (
                    <TrendingUp className="w-3 h-3 text-green-500" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-500" />
                  )}
                </span>
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {form.watch("displayMetrics").length > 0 && (
          <div className="flex flex-wrap gap-1">
            {form.watch("displayMetrics").map((metricName) => (
              <Badge key={metricName} variant="secondary" className="text-xs">
                {metricName}
              </Badge>
            ))}
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

