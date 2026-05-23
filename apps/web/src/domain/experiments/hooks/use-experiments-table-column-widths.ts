"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ProjectMetric } from "@/domain/projects/types";
import type { Experiment } from "@/domain/experiments/types";
import type { Metric } from "@/domain/metrics/types";
import { displayMetricKeyEquals, formatMetricLabel } from "@/lib/metrics/format-metric-label";
import { inferMetricColumnWidthPx } from "@/lib/table/column-width-inference";
import {
  buildDefaultExperimentsTableWidths,
  clampExperimentsColumnWidth,
  computeExperimentsTableTotalWidthPx,
  experimentsTableColumnPolicy,
  experimentsTableColumnWidthFallback,
  loadExperimentsTableWidths,
  mergeExperimentsTableWidths,
  metricColumnId,
  saveExperimentsTableWidths,
} from "@/domain/experiments/lib/experiments-table-column-widths";

function clientXFrom(ev: MouseEvent | TouchEvent): number {
  if ("touches" in ev && ev.touches.length > 0) {
    return ev.touches[0]!.clientX;
  }
  return (ev as MouseEvent).clientX;
}

type UseExperimentsTableColumnWidthsOptions = {
  experiments?: Experiment[];
  aggregatedMetrics?: Record<string, Metric[]>;
};

export function useExperimentsTableColumnWidths(
  projectId: string | undefined,
  metrics: ProjectMetric[],
  options: UseExperimentsTableColumnWidthsOptions = {}
) {
  const { experiments = [], aggregatedMetrics } = options;
  const inferredMetricWidths = useMemo(() => {
    const out: Record<string, number> = {};
    for (const metric of metrics) {
      const id = metricColumnId(metric);
      out[id] = inferMetricColumnWidthPx({
        header: formatMetricLabel(metric.name, metric.label ?? null),
        values: experiments.map((experiment) =>
          aggregatedMetrics?.[experiment.id]?.find((m) =>
            displayMetricKeyEquals(
              { name: m.name, label: m.label },
              { name: metric.name, label: metric.label ?? null }
            )
          )?.value
        ),
        minPx: experimentsTableColumnPolicy(id).minPx,
        maxPx: experimentsTableColumnPolicy(id).maxPx,
        chromePx: 64,
      });
    }
    return out;
  }, [aggregatedMetrics, experiments, metrics]);

  const defaultExperimentTableColumnWidths = useMemo(
    () => buildDefaultExperimentsTableWidths(metrics, inferredMetricWidths),
    [inferredMetricWidths, metrics]
  );
  const [experimentTableColumnWidths, setExperimentTableColumnWidths] = useState<Record<string, number>>(
    defaultExperimentTableColumnWidths
  );
  const [metricPxOverrideKeys, setMetricPxOverrideKeys] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    if (!projectId) return;
    const persisted = loadExperimentsTableWidths(projectId);
    // Existing table prefs are external localStorage state; this sync mirrors the app's other
    // persisted table controls and intentionally updates React state from the loaded snapshot.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMetricPxOverrideKeys(
      new Set(Object.keys(persisted ?? {}).filter((k) => k.startsWith("metric:")))
    );
    setExperimentTableColumnWidths(
      mergeExperimentsTableWidths(defaultExperimentTableColumnWidths, persisted)
    );
  }, [projectId, defaultExperimentTableColumnWidths]);

  const experimentTableResolvedColumnWidths = useMemo(
    () => ({ ...defaultExperimentTableColumnWidths, ...experimentTableColumnWidths }),
    [defaultExperimentTableColumnWidths, experimentTableColumnWidths]
  );

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!projectId) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      const persistedWidths: Record<string, number> = {};
      for (const [columnId, width] of Object.entries(experimentTableColumnWidths)) {
        if (columnId.startsWith("metric:") && !metricPxOverrideKeys.has(columnId)) continue;
        persistedWidths[columnId] = width;
      }
      saveExperimentsTableWidths(projectId, persistedWidths);
    }, 350);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, [projectId, experimentTableColumnWidths, metricPxOverrideKeys]);

  const startResize = useCallback(
    (columnId: string, clientX: number) => {
      if (columnId === "grip") return;
      const startW =
        experimentTableColumnWidths[columnId] ??
        defaultExperimentTableColumnWidths[columnId] ??
        experimentsTableColumnWidthFallback(columnId);
      const startX = clientX;

      const onMove = (ev: MouseEvent | TouchEvent) => {
        const x = clientXFrom(ev);
        const next = clampExperimentsColumnWidth(columnId, startW + (x - startX));
        setExperimentTableColumnWidths((w) => ({ ...w, [columnId]: next }));
      };

      const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        window.removeEventListener("touchmove", onMove);
        window.removeEventListener("touchend", onUp);
        window.removeEventListener("touchcancel", onUp);
        if (columnId.startsWith("metric:")) {
          setMetricPxOverrideKeys((prev) => {
            const n = new Set(prev);
            n.add(columnId);
            return n;
          });
        }
      };

      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
      window.addEventListener("touchmove", onMove, { passive: false });
      window.addEventListener("touchend", onUp);
      window.addEventListener("touchcancel", onUp);
    },
    [experimentTableColumnWidths, defaultExperimentTableColumnWidths]
  );

  const experimentTableTotalWidthPx = useMemo(
    () =>
      computeExperimentsTableTotalWidthPx(
        experimentTableResolvedColumnWidths,
        metricPxOverrideKeys,
        metrics
      ),
    [experimentTableResolvedColumnWidths, metricPxOverrideKeys, metrics]
  );

  return {
    experimentTableResolvedColumnWidths,
    metricPxOverrideKeys,
    startResize,
    experimentTableTotalWidthPx,
  };
}
