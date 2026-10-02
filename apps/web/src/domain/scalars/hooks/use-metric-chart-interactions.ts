import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import type { PlotMouseEvent } from "plotly.js";
import type { ChartDomain, ScalarPointSelection } from "../types";
import type { MetricChartProps } from "../components/metric-chart";
import { usesUnifiedMultiHover } from "../utils/metric-chart-hover";
import {
  buildMultiHoverState,
  pickNearestHoverPoint,
  isScalarWireValue,
  type MultiHoverState,
} from "../components/plotly/metric-chart-tooltip";

type RelayoutEvent = Readonly<Record<string, unknown>>;
type PlotlyGraphDiv = Readonly<HTMLElement> & {
  on?: (eventName: string, handler: (event: RelayoutEvent) => void) => void;
  removeListener?: (
    eventName: string,
    handler: (event: RelayoutEvent) => void,
  ) => void;
};

export function useMetricChartInteractions({
  zoom: { domain, onDomainChange } = {},
  hover: { hoverMode, hoverDisplayNames },
  onPointContextMenu,
}: {
  zoom: MetricChartProps["zoom"];
  hover: {
    hoverMode: NonNullable<
      NonNullable<MetricChartProps["display"]>["hoverMode"]
    >;
    hoverDisplayNames: Map<string, string>;
  };
  onPointContextMenu: NonNullable<
    MetricChartProps["interactions"]
  >["onPointContextMenu"];
}) {
  const [dragMode, setDragMode] = useState<"zoom" | "pan">("zoom");
  const activePointRef = useRef<ScalarPointSelection | null>(null);
  const relayoutingRef = useRef(false);
  const graphDivRef = useRef<PlotlyGraphDiv | null>(null);
  const [multiHover, setMultiHover] = useState<MultiHoverState | null>(null);

  const handleRelayout = useCallback(
    (event: RelayoutEvent) => {
      // End the drag-update freeze once Plotly commits the pan/zoom relayout.
      relayoutingRef.current = false;
      if (event?.dragmode === "zoom" || event?.dragmode === "pan") {
        setDragMode(event.dragmode);
      }
      const nextDomain: ChartDomain = {
        x: domain?.x ?? null,
        y: domain?.y ?? null,
      };

      if (
        event["xaxis.range[0]"] !== undefined &&
        event["xaxis.range[1]"] !== undefined
      ) {
        nextDomain.x = [
          Number(event["xaxis.range[0]"]),
          Number(event["xaxis.range[1]"]),
        ];
      } else if (event["xaxis.autorange"] === true) {
        nextDomain.x = null;
      }

      if (
        event["yaxis.range[0]"] !== undefined &&
        event["yaxis.range[1]"] !== undefined
      ) {
        nextDomain.y = [
          Number(event["yaxis.range[0]"]),
          Number(event["yaxis.range[1]"]),
        ];
      } else if (event["yaxis.autorange"] === true) {
        nextDomain.y = null;
      }

      onDomainChange?.(nextDomain);
    },
    [domain, onDomainChange],
  );

  const handleRelayouting = useCallback(() => {
    // Mark active Plotly drag so live scalar refreshes do not trigger Plotly.react mid-drag.
    relayoutingRef.current = true;
  }, []);
  const handleInitialized = useCallback(
    (_figure: unknown, graphDiv: Readonly<HTMLElement>) => {
      const plotlyGraphDiv = graphDiv as PlotlyGraphDiv;
      graphDivRef.current = plotlyGraphDiv;
      // react-plotly's TS types omit onRelayouting, so attach the native Plotly event.
      plotlyGraphDiv.on?.("plotly_relayouting", handleRelayouting);
    },
    [handleRelayouting],
  );
  const shouldFreezePlotUpdates = useCallback(() => relayoutingRef.current, []);

  useEffect(
    () => () => {
      graphDivRef.current?.removeListener?.(
        "plotly_relayouting",
        handleRelayouting,
      );
      graphDivRef.current = null;
    },
    [handleRelayouting],
  );

  const handleHover = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      if (usesUnifiedMultiHover(hoverMode)) {
        setMultiHover(
          buildMultiHoverState(event, hoverDisplayNames, {
            filterToVisibleYRange: hoverMode === "visible",
            domainY: domain?.y ?? null,
          }),
        );
      }
      const point = pickNearestHoverPoint(event);
      const customData = point?.customdata;
      if (!Array.isArray(customData) || customData.length < 6) return;
      const [
        experimentId,
        experimentName,
        pointMetricName,
        originalValue,
        smoothedValue,
        step,
      ] = customData;
      if (
        typeof experimentId !== "string" ||
        typeof experimentName !== "string" ||
        typeof pointMetricName !== "string" ||
        !isScalarWireValue(originalValue) ||
        !isScalarWireValue(smoothedValue) ||
        typeof step !== "number"
      ) {
        return;
      }
      activePointRef.current = {
        experimentId,
        experimentName,
        metricName: pointMetricName,
        step,
        originalValue,
        smoothedValue,
      };
    },
    [domain?.y, hoverDisplayNames, hoverMode],
  );

  const handleUnhover = useCallback(() => {
    activePointRef.current = null;
    setMultiHover(null);
  }, []);

  const handleContextMenu = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      const activePoint = activePointRef.current;
      if (!activePoint || !onPointContextMenu) return;
      event.preventDefault();
      onPointContextMenu(activePoint, { x: event.clientX, y: event.clientY });
    },
    [onPointContextMenu],
  );

  return {
    dragMode,
    multiHover,
    shouldFreezePlotUpdates,
    events: {
      handleInitialized,
      handleRelayout,
      handleHover,
      handleUnhover,
      handleContextMenu,
    },
  };
}
