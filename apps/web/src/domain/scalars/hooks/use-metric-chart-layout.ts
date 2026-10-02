import { useCallback, useMemo } from "react";
import type { Config, Layout } from "plotly.js";
import type { ScalarHoverMode } from "../types";
import type { MetricChartProps } from "../components/metric-chart";
import {
  getNextScalarHoverMode,
  usesUnifiedMultiHover,
} from "../utils/metric-chart-hover";
import {
  getPlotlyThemeLayout,
  useIsDarkMode,
} from "../components/plotly/plotly-theme";

type AxisWithUnifiedHoverTitle = NonNullable<Partial<Layout>["xaxis"]> & {
  unifiedhovertitle?: { text: string };
};

export function useMetricChartLayout({
  metricName,
  viewport: { height, isFullscreen },
  zoom: { domain, onDomainChange } = {},
  hover: { hoverMode, onHoverModeChange },
  dragMode,
}: {
  metricName: string;
  viewport: Required<
    Pick<NonNullable<MetricChartProps["viewport"]>, "height" | "isFullscreen">
  >;
  zoom: MetricChartProps["zoom"];
  hover: {
    hoverMode: ScalarHoverMode;
    onHoverModeChange?: (mode: ScalarHoverMode) => void;
  };
  dragMode: "zoom" | "pan";
}) {
  const isDark = useIsDarkMode();
  const handleResetAxes = useCallback(() => {
    onDomainChange?.({ x: null, y: null });
  }, [onDomainChange]);

  const layout = useMemo<Partial<Layout>>(() => {
    const themeLayout = getPlotlyThemeLayout(isDark);
    const tickSize = isFullscreen ? 12 : 10;
    const xAxis: AxisWithUnifiedHoverTitle = {
      ...themeLayout.xaxis,
      title: isFullscreen
        ? {
            text: "Step",
            font: { size: 12, color: isDark ? "#f7f8f8" : undefined },
          }
        : undefined,
      tickfont: { size: tickSize, color: isDark ? "#8a8f98" : undefined },
      range: domain?.x || undefined,
      autorange: domain?.x ? false : true,
      unifiedhovertitle: {
        text: "\u00A0",
      },
    };

    return {
      ...themeLayout,
      autosize: true,
      height: typeof height === "number" ? height : undefined,
      margin: {
        l: isFullscreen ? 60 : 50,
        r: 20,
        t: 10,
        b: isFullscreen ? 40 : 30,
      },
      xaxis: xAxis,
      yaxis: {
        ...themeLayout.yaxis,
        tickfont: { size: tickSize, color: isDark ? "#8a8f98" : undefined },
        range: domain?.y || undefined,
        autorange: domain?.y ? false : true,
      },
      showlegend: false,
      hovermode: usesUnifiedMultiHover(hoverMode) ? "x unified" : "closest",
      dragmode: dragMode,
      uirevision: metricName,
    };
  }, [
    domain?.x,
    domain?.y,
    dragMode,
    height,
    hoverMode,
    isDark,
    isFullscreen,
    metricName,
  ]);

  const config = useMemo<Partial<Config>>(() => {
    const modeBarButtonsToAdd = [
      {
        name: "Reset axes",
        title: "Reset axes",
        icon: RESET_AXES_ICON,
        click: handleResetAxes,
      },
    ];
    if (onHoverModeChange) {
      const presentation = getHoverModeButtonPresentation(hoverMode);
      const nextMode = getNextScalarHoverMode(hoverMode);
      modeBarButtonsToAdd.push({
        name: presentation.name,
        title: `${presentation.title} (click for ${getHoverModeButtonPresentation(nextMode).name.toLowerCase()})`,
        icon: presentation.icon,
        click: () => onHoverModeChange(nextMode),
      });
    }
    return {
      displayModeBar: true,
      modeBarButtonsToRemove: [
        "lasso2d",
        "select2d",
        "autoScale2d",
        "resetScale2d",
      ],
      modeBarButtonsToAdd,
      displaylogo: false,
      responsive: true,
      // Plotly's cartesian axis drag handles switch drags near edges into axis-only pan/zoom,
      // which feels like snapping while dragging scalar plots. Keep plot-area drag, remove handles.
      showAxisDragHandles: false,
      showAxisRangeEntryBoxes: false,
    };
  }, [handleResetAxes, hoverMode, onHoverModeChange]);

  return { layout, config };
}

const HOVER_NEAREST_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 450H880V550H120V450Z",
};

const RESET_AXES_ICON = {
  width: 1000,
  height: 1000,
  path: "M500 120C320 120 170 250 135 420H35L185 600L335 420H235C268 305 374 220 500 220C655 220 780 345 780 500C780 655 655 780 500 780C410 780 330 738 279 672L199 732C268 823 377 880 500 880C710 880 880 710 880 500C880 290 710 120 500 120Z",
};

const HOVER_ALL_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 220H880V320H120V220ZM120 450H880V550H120V450ZM120 680H880V780H120V680Z",
};

const HOVER_VISIBLE_ICON = {
  width: 1000,
  height: 1000,
  path: "M220 280H780V720H220V280ZM220 480H780",
};

function getHoverModeButtonPresentation(mode: ScalarHoverMode): {
  name: string;
  title: string;
  icon: { width: number; height: number; path: string };
} {
  switch (mode) {
    case "compare":
      return {
        name: "Hover all",
        title: "Show all experiments at this step",
        icon: HOVER_ALL_ICON,
      };
    case "visible":
      return {
        name: "Hover in view",
        title: "Show only experiments inside the visible y-axis range",
        icon: HOVER_VISIBLE_ICON,
      };
    case "nearest":
      return {
        name: "Hover nearest",
        title: "Show only the nearest experiment",
        icon: HOVER_NEAREST_ICON,
      };
  }
}
