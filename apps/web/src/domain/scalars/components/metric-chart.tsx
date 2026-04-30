"use client";

import { useCallback, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import type { Config, Layout } from "plotly.js";

type RelayoutEvent = Readonly<Record<string, unknown>>;

import type { Experiment } from "@/domain/experiments/types";
import type { ChartDomain } from "@/domain/scalars/types";
import { CHART_COLORS } from "@/domain/scalars/constants";

export interface MetricChartProps {
  data: Array<Record<string, number | null>>;
  selectedExperiments: Experiment[];
  allExperiments: Experiment[];
  height?: number;
  domain?: ChartDomain | null;
  onDomainChange?: (domain: ChartDomain | null) => void;
  isFullscreen?: boolean;
}

export function MetricChart({
  data,
  selectedExperiments,
  allExperiments,
  height = 200,
  domain,
  onDomainChange,
  isFullscreen = false,
}: MetricChartProps) {
  const [dragMode, setDragMode] = useState<"zoom" | "pan">("zoom");

  const plotData = useMemo(() => {
    return selectedExperiments.map((experiment) => {
      const originalIndex = allExperiments.findIndex((item) => item.id === experiment.id);
      const experimentColor = experiment.color || CHART_COLORS[originalIndex % CHART_COLORS.length];
      const xValues: number[] = [];
      const yValues: number[] = [];

      data.forEach((point) => {
        const step = point.step as number;
        const value = point[experiment.id];
        if (value !== null && value !== undefined) {
          xValues.push(step);
          yValues.push(value as number);
        }
      });

      return {
        x: xValues,
        y: yValues,
        type: "scatter" as const,
        mode: "lines" as const,
        name: experiment.name,
        line: {
          color: experimentColor,
          width: isFullscreen ? 2 : 1.5,
        },
        hovertemplate: `<b>${experiment.name}</b><br>Step: %{x}<br>Value: %{y:.4f}<extra></extra>`,
      };
    });
  }, [data, selectedExperiments, allExperiments, isFullscreen]);

  const handleRelayout = useCallback(
    (event: RelayoutEvent) => {
      if (event?.dragmode === "zoom" || event?.dragmode === "pan") {
        setDragMode(event.dragmode);
      }
      const nextDomain: ChartDomain = {
        x: domain?.x ?? null,
        y: domain?.y ?? null,
      };

      if (event["xaxis.range[0]"] !== undefined && event["xaxis.range[1]"] !== undefined) {
        nextDomain.x = [
          Number(event["xaxis.range[0]"]),
          Number(event["xaxis.range[1]"]),
        ];
      } else if (event["xaxis.autorange"] === true) {
        nextDomain.x = null;
      }

      if (event["yaxis.range[0]"] !== undefined && event["yaxis.range[1]"] !== undefined) {
        nextDomain.y = [
          Number(event["yaxis.range[0]"]),
          Number(event["yaxis.range[1]"]),
        ];
      } else if (event["yaxis.autorange"] === true) {
        nextDomain.y = null;
      }

      onDomainChange?.(nextDomain);
    },
    [domain, onDomainChange]
  );

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data for selected experiments
      </div>
    );
  }

  const layout: Partial<Layout> = {
    autosize: true,
    height,
    margin: {
      l: isFullscreen ? 60 : 50,
      r: 20,
      t: 10,
      b: isFullscreen ? 40 : 30,
    },
    xaxis: {
      title: isFullscreen ? { text: "Step", font: { size: 12 } } : undefined,
      tickfont: { size: isFullscreen ? 12 : 10 },
      gridcolor: "rgba(128, 128, 128, 0.2)",
      range: domain?.x || undefined,
      autorange: domain?.x ? false : true,
    },
    yaxis: {
      tickfont: { size: isFullscreen ? 12 : 10 },
      gridcolor: "rgba(128, 128, 128, 0.2)",
      range: domain?.y || undefined,
      autorange: domain?.y ? false : true,
    },
    showlegend: false,
    hovermode: "x unified" as const,
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    dragmode: dragMode,
  };

  const config: Partial<Config> = {
    displayModeBar: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    displaylogo: false,
    responsive: true,
  };

  return (
    <div style={{ height }}>
      <Plot
        data={plotData}
        layout={layout}
        config={config}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler={true}
        onRelayout={handleRelayout}
      />
    </div>
  );
}
