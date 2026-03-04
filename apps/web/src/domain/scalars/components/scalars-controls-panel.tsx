"use client";

import { ChevronDown, Eye, EyeOff, Maximize2, Pencil, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import type { Experiment } from "@/domain/experiments/types";
import { CHART_COLORS } from "@/domain/scalars/constants";
import type { SyncMode } from "@/domain/scalars/types";

export interface ScalarsControlsPanelProps {
  syncMode: SyncMode;
  setSyncMode: (mode: SyncMode) => void;
  soloMode: boolean;
  onToggleSoloMode: () => void;
  cardHeight: number;
  setCardHeight: (value: number) => void;
  cardMinWidth: number;
  setCardMinWidth: (value: number) => void;
  smoothing: number;
  onSmoothingChange: (value: number[]) => void;
  onSmoothingCommit: (value: number[]) => void;
  experiments: Experiment[];
  selectedExperimentIds: Set<string>;
  chosenExperimentId: string | null;
  setChosenExperimentId: (id: string) => void;
  onToggleExperiment: (experimentId: string) => void;
  onSelectAllExperiments: () => void;
  onClearAllExperiments: () => void;
  allLoggedMetricNames: string[];
  hiddenMetrics: Set<string>;
  onToggleMetric: (metricName: string) => void;
  onShowAllMetrics: () => void;
  onShowOnlyMetric: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  metricDomains: Record<string, { x: [number, number] | null; y: [number, number] | null }>;
  onResetMetricDomain: (metricName: string) => void;
  onEditExperiment: (experiment: Experiment) => void;
  onResetAllDomains: () => void;
}

export function ScalarsControlsPanel({
  syncMode,
  setSyncMode,
  soloMode,
  onToggleSoloMode,
  cardHeight,
  setCardHeight,
  cardMinWidth,
  setCardMinWidth,
  smoothing,
  onSmoothingChange,
  onSmoothingCommit,
  experiments,
  selectedExperimentIds,
  chosenExperimentId,
  setChosenExperimentId,
  onToggleExperiment,
  onSelectAllExperiments,
  onClearAllExperiments,
  allLoggedMetricNames,
  hiddenMetrics,
  onToggleMetric,
  onShowAllMetrics,
  onShowOnlyMetric,
  onExpandMetric,
  metricDomains,
  onResetMetricDomain,
  onEditExperiment,
  onResetAllDomains,
}: ScalarsControlsPanelProps) {
  return (
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
            onClick={onToggleSoloMode}
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
            <span className="text-sm font-mono w-12 text-right">{cardHeight}px</span>
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
            <span className="text-sm font-mono w-12 text-right">{cardMinWidth}px</span>
          </div>
        </div>

        <Separator />

        <div className="space-y-2">
          <Label className="text-sm font-medium">Smoothing</Label>
          <div className="flex items-center gap-3">
            <Slider
              value={[smoothing]}
              onValueChange={onSmoothingChange}
              onValueCommit={onSmoothingCommit}
              min={0}
              max={0.99}
              step={0.01}
              className="flex-1"
              data-testid="slider-smoothing"
            />
            <span className="text-sm font-mono w-10 text-right">{smoothing.toFixed(2)}</span>
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
                onClick={onSelectAllExperiments}
                data-testid="button-select-all-experiments"
              >
                All
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={onClearAllExperiments}
                data-testid="button-clear-all-experiments"
              >
                None
              </Button>
            </div>
          </div>
          <ScrollArea className="h-40">
            <div className="space-y-1 pr-3">
              {experiments.map((experiment, index) => (
                <div key={experiment.id} className="flex items-center gap-2 py-1">
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
                    id={`exp-${experiment.id}`}
                    checked={selectedExperimentIds.has(experiment.id)}
                    onCheckedChange={() => onToggleExperiment(experiment.id)}
                    data-testid={`checkbox-experiment-${index}`}
                  />
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: experiment.color || CHART_COLORS[index % CHART_COLORS.length] }}
                  />
                  <label
                    htmlFor={`exp-${experiment.id}`}
                    className="text-sm truncate cursor-pointer flex-1"
                    title={experiment.name}
                  >
                    {experiment.name}
                  </label>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => onEditExperiment(experiment)}
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
                onClick={onShowAllMetrics}
                data-testid="button-show-all-metrics"
              >
                Show All
              </Button>
            )}
          </div>
          <ScrollArea className="h-32">
            <div className="space-y-1 pr-3">
              {allLoggedMetricNames.map((metricName) => (
                <div key={metricName} className="flex items-center gap-1 py-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 flex-shrink-0"
                    onClick={() => onToggleMetric(metricName)}
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
                          className={`text-sm truncate flex-1 ${
                            hiddenMetrics.has(metricName) ? "text-muted-foreground line-through" : ""
                          }`}
                          title={metricName}
                        >
                          {metricName}
                        </span>
                        <ChevronDown className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                      </div>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                      <DropdownMenuItem
                        onClick={() => onShowOnlyMetric(metricName)}
                        data-testid={`menu-only-metric-${metricName}`}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        Show Only This
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onExpandMetric(metricName)}
                        disabled={hiddenMetrics.has(metricName)}
                        data-testid={`menu-expand-metric-${metricName}`}
                      >
                        <Maximize2 className="w-4 h-4 mr-2" />
                        Expand
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => onResetMetricDomain(metricName)}
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
            {Object.values(metricDomains).some((domain) => domain?.x || domain?.y) && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={onResetAllDomains}
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
  );
}
