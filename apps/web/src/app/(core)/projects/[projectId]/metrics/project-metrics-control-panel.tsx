"use client";

import { Database, Filter, Wrench } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { MetricLabelsResponse } from "@/domain/metrics/types";

type ControlPanelProps = {
  labelData: MetricLabelsResponse;
  label: string | null;
  onLabelChange: (v: string | null) => void;
  includeAll: boolean;
  onIncludeAllChange: (v: boolean) => void;
  nameFilter: string;
  onNameFilterChange: (v: string) => void;
  editMode: boolean;
  onEditModeChange: (v: boolean) => void;
};

/**
 * Left-rail control blocks (same width pattern as the Scalars page): stacked cards for label,
 * filter, and report/edit options. Persisted prefs live in localStorage; edit session in-memory.
 */
export function ProjectMetricsControlPanel({
  labelData,
  label,
  onLabelChange,
  includeAll,
  onIncludeAllChange,
  nameFilter,
  onNameFilterChange,
  editMode,
  onEditModeChange,
}: ControlPanelProps) {
  return (
    <aside
      className="flex w-full min-w-0 shrink-0 flex-col gap-3 self-start border-b border-border pb-3 pl-0 sm:w-72 sm:gap-4 sm:border-b-0 sm:pb-0 lg:max-h-full lg:min-h-0 lg:overflow-y-auto lg:self-stretch"
      aria-label="Metrics view controls"
    >
      <Card>
        <CardHeader className="space-y-1 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Database className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span>Data source</span>
          </div>
          <CardDescription>Label and which experiments load in the grid.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
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
                {labelData.hasUnlabeled ? <SelectItem value="__empty__">Unlabeled (empty string)</SelectItem> : null}
                {labelData.labels.map((l) => (
                  <SelectItem key={l} value={l}>
                    {l}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
          <CardDescription>Client-side: narrows the loaded rows only.</CardDescription>
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
          <CardDescription>Toggle controls for row/column and cell marks (session only).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-0">
          <div className="flex shrink-0 items-center gap-2">
            <Switch id="edit-mode" checked={editMode} onCheckedChange={onEditModeChange} data-testid="switch-edit-mode" />
            <Label htmlFor="edit-mode" className="text-sm">
              Edit mode
            </Label>
          </div>
          <p className="text-xs leading-snug text-muted-foreground">
            <strong>On</strong> — all rows; each column (including <span className="font-mono text-[11px]">experimentId</span> and{" "}
            <span className="font-mono text-[11px]">createdAt</span> on the right) has a <strong>Col</strong> toggle.
            <strong> Off</strong> — the report (which columns/rows, tints, min/max bold) applies. Session resets on
            reload.
          </p>
        </CardContent>
      </Card>
    </aside>
  );
}
