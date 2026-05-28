"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Config, Layout, PlotData } from "plotly.js";
import { Button } from "@/components/ui/button";
import { MemoizedPlot } from "@/domain/scalars/components/plotly/stable-plot";

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

/** Plotly.react transitions work reliably for scatter; histogram/bar when trace shape is unchanged. */
const PLOTLY_ARTIFACT_TRANSITION_MS = 200;

function artifactTypeSupportsPlotlyTransition(objectType: string): boolean {
  return objectType === "scatter" || objectType === "histogram";
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
  const previewPayload = useMemo(
    () => previewPayloadFromMetadata(objectType, metadata),
    [objectType, metadata?.preview_data, metadata?.preview_kind]
  );
  const needsFullDataInitially =
    objectType === "pie" ||
    objectType === "point_cloud_3d" ||
    !previewPayload;
  const [fullPayload, setFullPayload] = useState<PlotlyArtifactPayload | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastDisplayedPayloadRef = useRef<PlotlyArtifactPayload | null>(null);
  const prevTraceTypeKeyRef = useRef<string | null>(null);
  const [plotRevision, setPlotRevision] = useState(0);

  const activePayload = fullPayload ?? previewPayload;
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
    const { transition: _payloadTransition, ...payloadLayout } = payload?.layout ?? {};
    return {
      autosize: true,
      margin: { l: 40, r: 16, t: 32, b: 36 },
      ...payloadLayout,
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
  }, [enablePlotlyTransition, objectType, payload, title]);
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
    setFullPayload(null);
  }, [src]);

  useEffect(() => {
    if (!needsFullDataInitially) return;
    const controller = new AbortController();
    void loadFullPlotlyPayload(
      src,
      controller.signal,
      setLoadingFull,
      setError,
      setFullPayload
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
            setFullPayload
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
        className="w-full overflow-hidden rounded border"
        style={{ height: maxHeight }}
      >
        <MemoizedPlot
          data={plotData}
          layout={plotLayout}
          config={plotConfig}
          revision={plotRevision}
        />
      </div>
      {(objectType === "histogram" || objectType === "scatter") && !fullPayload ? (
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
              setFullPayload
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
