"use client";

import { memo } from "react";
import Plot from "react-plotly.js";
import type { Config, Layout, PlotData, PlotMouseEvent } from "plotly.js";

export const PLOT_STYLE = { width: "100%", height: "100%" };

export interface StablePlotProps {
  data: Partial<PlotData>[];
  layout: Partial<Layout>;
  config: Partial<Config>;
  revision?: number;
  shouldFreezeUpdates?: () => boolean;
  onHover?: (event: Readonly<PlotMouseEvent>) => void;
  onUnhover?: () => void;
  onRelayout?: (event: Readonly<Record<string, unknown>>) => void;
  onInitialized?: (_figure: unknown, graphDiv: Readonly<HTMLElement>) => void;
}

function StablePlot({
  data,
  layout,
  config,
  revision,
  shouldFreezeUpdates,
  onHover,
  onUnhover,
  onRelayout,
  onInitialized,
}: StablePlotProps) {
  return (
    <Plot
      data={data}
      layout={layout}
      config={config}
      revision={revision}
      style={PLOT_STYLE}
      useResizeHandler={true}
      onHover={onHover}
      onUnhover={onUnhover}
      onRelayout={onRelayout}
      onInitialized={onInitialized}
    />
  );
}

/**
 * Keeps one Plotly instance per mount and updates via Plotly.react when props change.
 * Reference-stable data/layout/config are required for meaningful memoization.
 */
export const MemoizedPlot = memo(StablePlot, (prev, next) => {
  if (next.shouldFreezeUpdates?.()) {
    return true;
  }
  return (
    prev.data === next.data &&
    prev.layout === next.layout &&
    prev.config === next.config &&
    prev.revision === next.revision &&
    prev.onHover === next.onHover &&
    prev.onUnhover === next.onUnhover &&
    prev.onRelayout === next.onRelayout &&
    prev.onInitialized === next.onInitialized &&
    prev.shouldFreezeUpdates === next.shouldFreezeUpdates
  );
});
