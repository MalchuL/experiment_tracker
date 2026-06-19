"use client";

import { ArrowDownUp, Database, Filter, Wrench } from "lucide-react";
import { MetricsOrderList } from "./components/metrics-order-list";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { MetricLabelsResponse } from "@/domain/metrics/types";
import { cn } from "@/lib/utils";

type ControlPanelProps = {
  controlsOpen: boolean;
  labelData: MetricLabelsResponse;
  label: string | null;
  onLabelChange: (v: string | null) => void;
  includeAll: boolean;
  onIncludeAllChange: (v: boolean) => void;
  nameFilter: string;
  onNameFilterChange: (v: string) => void;
  editMode: boolean;
  onEditModeChange: (v: boolean) => void;
  pinLeadColumns: boolean;
  onPinLeadColumnsChange: (v: boolean) => void;
  wrapExperimentNames: boolean;
  onWrapExperimentNamesChange: (v: boolean) => void;
  wrapValues: boolean;
  onWrapValuesChange: (v: boolean) => void;
  orderedMetricNames: string[];
  onMetricReorder: (names: string[]) => void;
};

/**
 * Left-rail control blocks (same width pattern as the Scalars page): stacked cards for label,
 * filter, and report/edit options. The selected label owns the metric columns shown in the table.
 * Persisted prefs live in localStorage; edit session in-memory.
 */
export function ProjectMetricsControlPanel({
  controlsOpen,
  labelData,
  label,
  onLabelChange,
  includeAll,
  onIncludeAllChange,
  nameFilter,
  onNameFilterChange,
  editMode,
  onEditModeChange,
  pinLeadColumns,
  onPinLeadColumnsChange,
  wrapExperimentNames,
  onWrapExperimentNamesChange,
  wrapValues,
  onWrapValuesChange,
  orderedMetricNames,
  onMetricReorder,
}: ControlPanelProps) {
  return (
    <div
      className={cn(
        "relative shrink-0 self-start transition-all duration-300 lg:self-stretch",
        controlsOpen ? "w-full sm:w-72" : "w-0",
      )}
    >
      <aside
        className={cn(
          "flex min-w-0 flex-col gap-3 border-b border-border pb-3 pl-0 sm:gap-4 sm:border-b-0 sm:pb-0 lg:max-h-full lg:min-h-0 lg:overflow-y-auto",
          !controlsOpen && "invisible overflow-hidden",
        )}
        aria-label="Metrics view controls"
        aria-hidden={!controlsOpen}
      >
      <Card>
        <CardHeader className="space-y-1 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Database className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span>Data source</span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="pm-label">Label</Label>
              <Select
                value={label === null ? undefined : label === "" ? "__empty__" : label}
                onValueChange={(v) => (v === "__empty__" ? onLabelChange("") : onLabelChange(v))}
              >
                <SelectTrigger id="pm-label" className="w-full">
                  <SelectValue placeholder="Select label" />
                </SelectTrigger>
                <SelectContent>
                  {labelData.hasUnlabeled ? (
                    <SelectItem value="__empty__">Unlabeled (empty string)</SelectItem>
                  ) : null}
                  {labelData.labels.map((l) => (
                    <SelectItem key={l} value={l}>
                      {l}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="include-all"
              checked={includeAll}
              onCheckedChange={(c) => onIncludeAllChange(!!c)}
            />
            <Label htmlFor="include-all" className="text-sm font-normal leading-tight">
              Include experiments with no value for this label
            </Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="space-y-1 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Filter className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span>Table filter</span>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-1.5">
            <Label htmlFor="name-filter">Experiment name contains</Label>
            <Input
              id="name-filter"
              value={nameFilter}
              onChange={(e) => onNameFilterChange(e.target.value)}
              placeholder="e.g. baseline, seed…"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="space-y-1 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Wrench className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span>Report &amp; layout</span>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-0">
          <div className="flex shrink-0 items-center gap-2">
            <Switch
              id="pin-metric-experiment"
              checked={pinLeadColumns}
              onCheckedChange={onPinLeadColumnsChange}
            />
            <Label htmlFor="pin-metric-experiment" className="text-sm">
              Pin experiment column when scrolling horizontally
            </Label>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Switch
              id="wrap-experiment-names"
              checked={wrapExperimentNames}
              onCheckedChange={onWrapExperimentNamesChange}
            />
            <Label
              htmlFor="wrap-experiment-names"
              className="text-sm"
              title="Wrap long experiment names onto multiple lines."
            >
              Wrap experiment names
            </Label>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Switch
              id="wrap-values"
              checked={wrapValues}
              onCheckedChange={onWrapValuesChange}
            />
            <Label
              htmlFor="wrap-values"
              className="text-sm"
              title="Wrap long metric values onto multiple lines. Turn off to truncate to one line."
            >
              Wrap values
            </Label>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Switch id="edit-mode" checked={editMode} onCheckedChange={onEditModeChange} data-testid="switch-edit-mode" />
            <Label htmlFor="edit-mode" className="text-sm">
              Edit mode
            </Label>
          </div>
        </CardContent>
      </Card>

      {orderedMetricNames.length > 0 ? (
        <Card>
          <CardHeader className="space-y-1 pb-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <ArrowDownUp className="h-4 w-4 text-muted-foreground" aria-hidden />
              <span>Metric order</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            <p className="text-xs text-muted-foreground">Drag to reorder metric columns in the table.</p>
            <MetricsOrderList metricNames={orderedMetricNames} onReorder={onMetricReorder} />
          </CardContent>
        </Card>
      ) : null}
      </aside>
    </div>
  );
}
