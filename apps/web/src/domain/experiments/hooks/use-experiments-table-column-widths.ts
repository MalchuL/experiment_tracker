"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ProjectMetric } from "@/domain/projects/types";
import {
  buildDefaultExperimentsTableWidths,
  clampExperimentsColumnWidth,
  experimentsTableColumnWidthFallback,
  loadExperimentsTableWidths,
  mergeExperimentsTableWidths,
  saveExperimentsTableWidths,
} from "@/domain/experiments/lib/experiments-table-column-widths";

function clientXFrom(ev: MouseEvent | TouchEvent): number {
  if ("touches" in ev && ev.touches.length > 0) {
    return ev.touches[0]!.clientX;
  }
  return (ev as MouseEvent).clientX;
}

export function useExperimentsTableColumnWidths(projectId: string | undefined, metrics: ProjectMetric[]) {
  const defaultExperimentTableColumnWidths = useMemo(
    () => buildDefaultExperimentsTableWidths(metrics),
    [metrics]
  );
  const [experimentTableColumnWidths, setExperimentTableColumnWidths] = useState<Record<string, number>>(
    defaultExperimentTableColumnWidths
  );

  useEffect(() => {
    if (!projectId) return;
    setExperimentTableColumnWidths(
      mergeExperimentsTableWidths(
        defaultExperimentTableColumnWidths,
        loadExperimentsTableWidths(projectId)
      )
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
      saveExperimentsTableWidths(projectId, experimentTableColumnWidths);
    }, 350);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, [projectId, experimentTableColumnWidths]);

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
      Object.values(experimentTableResolvedColumnWidths).reduce(
        (sum, n) => sum + (typeof n === "number" ? n : 0),
        0
      ),
    [experimentTableResolvedColumnWidths]
  );

  return {
    experimentTableResolvedColumnWidths,
    startResize,
    experimentTableTotalWidthPx,
  };
}
