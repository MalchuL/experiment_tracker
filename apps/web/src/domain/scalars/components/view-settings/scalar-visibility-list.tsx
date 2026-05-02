"use client";

import { Eye, EyeOff, Maximize2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ArtifactViewItem, ChartDomain } from "@/domain/scalars/types";

interface ScalarVisibilityListProps {
  allLoggedMetricNames: string[];
  hiddenMetrics: Set<string>;
  artifactItems: ArtifactViewItem[];
  hiddenArtifactIds: Set<string>;
  metricDomains: Record<string, ChartDomain>;
  onToggleMetric: (metricName: string) => void;
  onShowAllMetrics: () => void;
  onShowOnlyMetric: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onResetMetricDomain: (metricName: string) => void;
  onToggleArtifact: (artifactId: string) => void;
  onOpenArtifact: (artifactId: string) => void;
}

export function ScalarVisibilityList({
  allLoggedMetricNames,
  hiddenMetrics,
  artifactItems,
  hiddenArtifactIds,
  metricDomains,
  onToggleMetric,
  onShowAllMetrics,
  onShowOnlyMetric,
  onExpandMetric,
  onResetMetricDomain,
  onToggleArtifact,
  onOpenArtifact,
}: ScalarVisibilityListProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {allLoggedMetricNames.length - hiddenMetrics.size}/{allLoggedMetricNames.length} scalars
        </span>
        {hiddenMetrics.size > 0 ? (
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onShowAllMetrics}>
            Show all
          </Button>
        ) : null}
      </div>
      <ScrollArea className="h-[24vh] min-h-40">
        <div className="space-y-0.5 pr-3">
          {allLoggedMetricNames.map((metricName) => {
            const isHidden = hiddenMetrics.has(metricName);
            return (
              <div key={metricName} className="flex items-center gap-1 rounded px-1 py-0.5 hover:bg-muted/50">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={() => onToggleMetric(metricName)}
                  data-testid={`button-toggle-metric-${metricName}`}
                >
                  {isHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                </Button>
                <button
                  type="button"
                  className={`min-w-0 flex-1 truncate text-left text-xs ${
                    isHidden ? "text-muted-foreground line-through" : ""
                  }`}
                  title={metricName}
                  onClick={() => onShowOnlyMetric(metricName)}
                >
                  {metricName}
                </button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={() => onExpandMetric(metricName)}
                  disabled={isHidden}
                  title="Expand"
                >
                  <Maximize2 className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={() => onResetMetricDomain(metricName)}
                  disabled={!metricDomains[metricName]}
                  title="Reset zoom"
                >
                  <RotateCcw className="h-3 w-3" />
                </Button>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {artifactItems.length > 0 ? (
        <div className="space-y-1">
          <div className="text-[11px] font-medium text-muted-foreground">Artifacts</div>
          <ScrollArea className="h-28">
            <div className="space-y-0.5 pr-3">
              {artifactItems.map((artifact) => {
                const isHidden = hiddenArtifactIds.has(artifact.id);
                return (
                  <div key={artifact.id} className="flex items-center gap-1 rounded px-1 py-0.5 hover:bg-muted/50">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 shrink-0"
                      onClick={() => onToggleArtifact(artifact.id)}
                    >
                      {isHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                    </Button>
                    <button
                      type="button"
                      className={`min-w-0 flex-1 truncate text-left text-xs ${
                        isHidden ? "text-muted-foreground line-through" : ""
                      }`}
                      title={artifact.label}
                      onClick={() => onOpenArtifact(artifact.id)}
                    >
                      {artifact.label}
                    </button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 shrink-0"
                      onClick={() => onOpenArtifact(artifact.id)}
                      disabled={isHidden}
                    >
                      <Maximize2 className="h-3 w-3" />
                    </Button>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </div>
      ) : null}
    </div>
  );
}
