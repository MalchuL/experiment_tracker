"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Config, Layout, PlotData } from "plotly.js";
import { Button } from "@/components/ui/button";
import { MemoizedPlot } from "@/domain/scalars/components/plotly/stable-plot";
import {
  getPlotlyThemeLayout,
  useIsDarkMode,
} from "@/domain/scalars/components/plotly/plotly-theme";

export interface PlotlyArtifactMediaProps {
  objectType: string;
  src: string;
  title: string;
  maxHeight: number;
  metadata?: Record<string, string>;
}

interface PlotlyArtifactPayload {
  schemaVersion?: number;
  data?: Partial<PlotData>[];
  layout?: Partial<Layout>;
  config?: Partial<Config>;
}

export function isPlotlyArtifactType(objectType: string): boolean {
  return (
    objectType === "histogram" ||
    objectType === "pie" ||
    objectType === "scatter" ||
    objectType === "point_cloud_3d"
  );
}

function previewPayloadFromMetadata(
  objectType: string,
  metadata?: Record<string, string>
): PlotlyArtifactPayload | null {
  if (!metadata?.preview_data) return null;
  try {
    const preview = JSON.parse(metadata.preview_data) as Record<string, unknown>;
    if (
      metadata.preview_kind === "histogram_bins" &&
      Array.isArray(preview.bins) &&
      Array.isArray(preview.counts)
    ) {
      const bins = preview.bins as number[];
      const counts = preview.counts as number[];
      const x = counts.map((_, index) => {
        const left = Number(bins[index] ?? index);
        const right = Number(bins[index + 1] ?? left);
        return (left + right) / 2;
      });
      const width = counts.map((_, index) =>
        Math.max(0, Number(bins[index + 1]) - Number(bins[index]))
      );
      return {
        data: [{ type: "bar", x, y: counts, width, name: "preview" }],
        layout: { title: { text: "Preview" }, bargap: 0.05 },
        config: { responsive: true },
      };
    }
    if (
      metadata.preview_kind === "scatter_points" &&
      Array.isArray(preview.x) &&
      Array.isArray(preview.y)
    ) {
      return {
        data: [
          {
            type: "scatter",
            mode: "markers",
            x: preview.x as number[],
            y: preview.y as number[],
            name: "preview",
          },
        ],
        layout: { title: { text: "Preview" } },
        config: { responsive: true },
      };
    }
  } catch {
    return null;
  }
  return null;
}

function normalizePlotlyPayload(value: unknown): PlotlyArtifactPayload | null {
  if (!value || typeof value !== "object") return null;
  const payload = value as PlotlyArtifactPayload;
  if (!Array.isArray(payload.data)) return null;
  return {
    data: payload.data,
    layout: payload.layout ?? {},
    config: payload.config ?? { responsive: true },
  };
}

/** Plotly.react transitions work reliably for scatter when trace shape is unchanged. */
const PLOTLY_ARTIFACT_TRANSITION_MS = 200;

function artifactTypeSupportsPlotlyTransition(objectType: string): boolean {
  return objectType === "scatter";
}

function artifactUsesCartesianAxes(objectType: string): boolean {
  return objectType === "histogram" || objectType === "scatter";
}

function defaultPlotMargins(objectType: string): Partial<Layout>["margin"] {
  if (objectType === "pie") {
    return { l: 8, r: 8, t: 32, b: 8 };
  }
  return { l: 40, r: 16, t: 32, b: 36 };
}

function traceTypeKey(data: Partial<PlotData>[]): string {
  return data.map((trace) => String(trace.type ?? "")).join("|");
}

function withStableTraceUids(
  data: Partial<PlotData>[],
  objectType: string
): Partial<PlotData>[] {
  return data.map((trace, index) => ({
    ...trace,
    uid: trace.uid ?? `${objectType}-${index}`,
  }));
}

export function PlotlyArtifactMedia({
  objectType,
  src,
  title,
  maxHeight,
  metadata,
}: PlotlyArtifactMediaProps) {
  const isDark = useIsDarkMode();
  const previewPayload = useMemo(
    () => previewPayloadFromMetadata(objectType, metadata),
    [objectType, metadata?.preview_data, metadata?.preview_kind]
  );
  const needsFullDataInitially =
    objectType === "pie" ||
    objectType === "point_cloud_3d" ||
    !previewPayload;
  const [fullPayload, setFullPayload] = useState<PlotlyArtifactPayload | null>(null);
  const fullPayloadSrcRef = useRef<string | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastDisplayedPayloadRef = useRef<PlotlyArtifactPayload | null>(null);
  const prevTraceTypeKeyRef = useRef<string | null>(null);
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const lastSizedContainerRef = useRef<{ width: number; height: number } | null>(null);
  const [plotRevision, setPlotRevision] = useState(0);

  const fullPayloadForSrc =
    fullPayloadSrcRef.current === src ? fullPayload : null;
  const activePayload = fullPayloadForSrc ?? previewPayload;
  if (activePayload) {
    lastDisplayedPayloadRef.current = activePayload;
  }
  const payload = activePayload ?? lastDisplayedPayloadRef.current;

  const plotData = useMemo(
    () => withStableTraceUids(payload?.data ?? [], objectType),
    [objectType, payload]
  );
  const traceTypeKeyValue = traceTypeKey(plotData);
  const traceStructureChanged =
    prevTraceTypeKeyRef.current !== null &&
    prevTraceTypeKeyRef.current !== traceTypeKeyValue;
  const enablePlotlyTransition =
    artifactTypeSupportsPlotlyTransition(objectType) && !traceStructureChanged;

  useEffect(() => {
    prevTraceTypeKeyRef.current = traceTypeKeyValue;
  }, [traceTypeKeyValue]);

  const plotLayout = useMemo<Partial<Layout>>(() => {
    const themeLayout = getPlotlyThemeLayout(isDark);
    const { transition: _payloadTransition, ...payloadLayout } = payload?.layout ?? {};
    const usesCartesianAxes = artifactUsesCartesianAxes(objectType);
    const layout: Partial<Layout> = {
      autosize: true,
      margin: defaultPlotMargins(objectType),
      ...payloadLayout,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: themeLayout.font,
      hoverlabel: themeLayout.hoverlabel,
      title: payload?.layout?.title ?? { text: title },
      uirevision: `${objectType}:${title}`,
      ...(enablePlotlyTransition
        ? {
            transition: {
              duration: PLOTLY_ARTIFACT_TRANSITION_MS,
              easing: "cubic-in-out",
            },
          }
        : {}),
    };
    if (usesCartesianAxes) {
      layout.xaxis = {
        ...payloadLayout.xaxis,
        ...themeLayout.xaxis,
      };
      layout.yaxis = {
        ...payloadLayout.yaxis,
        ...themeLayout.yaxis,
      };
    }
    return layout;
  }, [enablePlotlyTransition, isDark, objectType, payload, title]);
  const plotConfig = useMemo<Partial<Config>>(
    () => ({
      responsive: true,
      displaylogo: false,
      ...(payload?.config ?? {}),
    }),
    [payload]
  );

  useEffect(() => {
    if (!payload) return;
    setPlotRevision((revision) => revision + 1);
  }, [payload]);

  useEffect(() => {
    const element = plotContainerRef.current;
    if (!element || !payload) return;

    const relayoutIfSized = (width: number, height: number) => {
      if (width <= 0 || height <= 0) {
        lastSizedContainerRef.current = null;
        return;
      }
      const previous = lastSizedContainerRef.current;
      if (previous?.width === width && previous?.height === height) return;
      lastSizedContainerRef.current = { width, height };
      setPlotRevision((revision) => revision + 1);
    };

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      relayoutIfSized(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(element);
    relayoutIfSized(element.clientWidth, element.clientHeight);

    return () => observer.disconnect();
  }, [payload]);

  useEffect(() => {
    if (!needsFullDataInitially) return;
    const controller = new AbortController();
    void loadFullPlotlyPayload(
      src,
      controller.signal,
      setLoadingFull,
      setError,
      (payload) => {
        if (controller.signal.aborted) return;
        fullPayloadSrcRef.current = src;
        setFullPayload(payload);
      }
    );
    return () => {
      controller.abort();
    };
  }, [needsFullDataInitially, src]);

  if (error && !payload) {
    return <p className="text-xs text-destructive">{error}</p>;
  }
  if (!payload) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={loadingFull}
        onClick={() =>
          void loadFullPlotlyPayload(
            src,
            undefined,
            setLoadingFull,
            setError,
            (payload) => {
              fullPayloadSrcRef.current = src;
              setFullPayload(payload);
            }
          )
        }
      >
        Load plot
      </Button>
    );
  }
  return (
    <div className="space-y-2">
      <div
        ref={plotContainerRef}
        className="w-full overflow-hidden rounded"
        style={{ height: maxHeight }}
      >
        <MemoizedPlot
          data={plotData}
          layout={plotLayout}
          config={plotConfig}
          revision={plotRevision}
        />
      </div>
      {(objectType === "histogram" || objectType === "scatter") && !fullPayloadForSrc ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loadingFull}
          onClick={() =>
            void loadFullPlotlyPayload(
              src,
              undefined,
              setLoadingFull,
              setError,
              (payload) => {
                fullPayloadSrcRef.current = src;
                setFullPayload(payload);
              }
            )
          }
        >
          Show all data
        </Button>
      ) : null}
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

async function loadFullPlotlyPayload(
  src: string,
  signal: AbortSignal | undefined,
  setLoading: (value: boolean) => void,
  setError: (value: string | null) => void,
  setPayload: (value: PlotlyArtifactPayload | null) => void
) {
  setLoading(true);
  setError(null);
  try {
    const response = await fetch(src, { signal });
    if (!response.ok) {
      throw new Error(`Failed to load plot (${response.status})`);
    }
    const payload = normalizePlotlyPayload(await response.json());
    if (!payload) {
      throw new Error("Invalid Plotly artifact payload");
    }
    setPayload(payload);
  } catch (error: unknown) {
    if (signal?.aborted) return;
    setError(error instanceof Error ? error.message : "Failed to load plot");
  } finally {
    if (!signal?.aborted) {
      setLoading(false);
    }
  }
}
