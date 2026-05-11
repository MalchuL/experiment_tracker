"use client";

import { useEffect, useMemo, useState } from "react";
import { LineChart } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAggregatedMetrics } from "@/domain/experiments/hooks/aggregated-metrics-hook";
import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";
import { useReportEditorContext } from "../report-editor-context";
import { ExperimentIdsField } from "./experiment-ids-field";
import { ReportBlockChrome } from "./report-block-chrome";
import type { MetricEmbedAttrs } from "./types";

export interface MetricEmbedBlockProps {
  attrs: MetricEmbedAttrs;
  onAttrsChange: (patch: Partial<MetricEmbedAttrs>) => void;
  selected?: boolean;
  editable?: boolean;
}

/**
 * Metric summary embed — pure UI + data preview. Tiptap node views only wire attrs.
 */
export function MetricEmbedBlock({
  attrs,
  onAttrsChange,
  selected,
  editable = true,
}: MetricEmbedBlockProps) {
  const { projectId, experiments } = useReportEditorContext();
  const { aggregatedMetricsPlain, isLoading } = useAggregatedMetrics(projectId);
  const [metricFilterText, setMetricFilterText] = useState(
    () => attrs.metricNames.join(", "),
  );

  useEffect(() => {
    setMetricFilterText(attrs.metricNames.join(", "));
  }, [attrs.metricNames]);

  const rows = useMemo(() => {
    const expSet = new Set(attrs.experimentIds);
    const nameFilters = attrs.metricNames.map((n) => n.trim().toLowerCase()).filter(Boolean);
    return aggregatedMetricsPlain.filter((m) => {
      if (attrs.experimentIds.length > 0 && !expSet.has(m.experimentId)) {
        return false;
      }
      if (nameFilters.length === 0) {
        return true;
      }
      return nameFilters.some((f) => m.name.toLowerCase().includes(f));
    });
  }, [aggregatedMetricsPlain, attrs.experimentIds, attrs.metricNames]);

  const applyMetricNames = () => {
    const names = metricFilterText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    onAttrsChange({ metricNames: names });
  };

  return (
    <ReportBlockChrome
      icon={LineChart}
      title="Metrics"
      description="Snapshot of logged metrics for the experiments you select."
      selected={selected}
    >
      <ExperimentIdsField
        experiments={experiments}
        value={attrs.experimentIds}
        onChange={(experimentIds) => onAttrsChange({ experimentIds })}
        disabled={!editable}
      />
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground">
          Metric names (optional, comma-separated)
        </Label>
        <div className="flex gap-2">
          <Input
            value={metricFilterText}
            disabled={!editable}
            onChange={(e) => setMetricFilterText(e.target.value)}
            onBlur={applyMetricNames}
            placeholder="e.g. loss, accuracy"
            className="h-8 text-sm"
          />
        </div>
      </div>
      <div className="rounded-md border border-dashed border-border bg-muted/30 px-2 py-2 text-xs">
        {isLoading ? (
          <span className="text-muted-foreground">Loading metrics…</span>
        ) : rows.length === 0 ? (
          <span className="text-muted-foreground">
            No metrics match this configuration yet.
          </span>
        ) : (
          <ul className="max-h-40 space-y-1 overflow-auto">
            {rows.slice(0, 40).map((m) => {
              const expName =
                experiments.find((e) => e.id === m.experimentId)?.name ?? m.experimentId;
              return (
                <li key={m.id} className="flex justify-between gap-2">
                  <span className="truncate text-muted-foreground">
                    {expName} · {m.name}
                    {m.label ? ` (${m.label})` : ""}
                  </span>
                  <span className="shrink-0 font-mono tabular-nums">
                    {formatMetricScalarForDisplay(m.value)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
        {rows.length > 40 ? (
          <p className="mt-1 text-[10px] text-muted-foreground">Showing first 40 rows.</p>
        ) : null}
      </div>
    </ReportBlockChrome>
  );
}
