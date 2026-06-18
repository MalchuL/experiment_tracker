"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_PREFIX = "experiment-tracker:experiment-data-compare:";
const LEAD_COLUMN = "lead";
const DEFAULT_LEAD_WIDTH = 256;
const DEFAULT_DATA_WIDTH = 224;
const MIN_LEAD_WIDTH = 160;
const MIN_DATA_WIDTH = 140;

type Widths = Record<string, number>;

function storageKey(scope: string, suffix: string): string {
  return `${STORAGE_PREFIX}${scope}:${suffix}`;
}

function minimumWidth(column: string): number {
  return column === LEAD_COLUMN ? MIN_LEAD_WIDTH : MIN_DATA_WIDTH;
}

function defaultWidth(column: string): number {
  return column === LEAD_COLUMN ? DEFAULT_LEAD_WIDTH : DEFAULT_DATA_WIDTH;
}

function loadWidths(scope: string): Widths {
  if (typeof window === "undefined") return { [LEAD_COLUMN]: DEFAULT_LEAD_WIDTH };
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey(scope, "widths")) ?? "{}") as Widths;
    const widths: Widths = { [LEAD_COLUMN]: DEFAULT_LEAD_WIDTH };
    for (const [column, value] of Object.entries(parsed)) {
      if (typeof value !== "number" || !Number.isFinite(value)) continue;
      widths[column] = Math.max(minimumWidth(column), value);
    }
    return widths;
  } catch {
    return { [LEAD_COLUMN]: DEFAULT_LEAD_WIDTH };
  }
}

export function loadCompareBoolean(scope: string, setting: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    const value = localStorage.getItem(storageKey(scope, setting));
    if (value === null) return fallback;
    return value === "1" || value === "true";
  } catch {
    return fallback;
  }
}

export function saveCompareBoolean(scope: string, setting: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(storageKey(scope, setting), value ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function loadCompareString(scope: string, setting: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  try {
    const value = localStorage.getItem(storageKey(scope, setting));
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

export function saveCompareString(scope: string, setting: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(storageKey(scope, setting), value);
  } catch {
    /* ignore */
  }
}

export function useExperimentDataCompareLayout(scope: string) {
  const [widths, setWidths] = useState<Widths>(() => loadWidths(scope));

  useEffect(() => {
    setWidths(loadWidths(scope));
  }, [scope]);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey(scope, "widths"), JSON.stringify(widths));
    } catch {
      /* ignore */
    }
  }, [scope, widths]);

  const widthFor = useCallback(
    (column: string) => widths[column] ?? defaultWidth(column),
    [widths]
  );

  const startResize = useCallback(
    (column: string, clientX: number) => {
      const startWidth = widthFor(column);
      const onMove = (event: MouseEvent | TouchEvent) => {
        const nextX = "touches" in event ? event.touches[0]?.clientX : event.clientX;
        if (nextX == null) return;
        setWidths((current) => ({
          ...current,
          [column]: Math.max(minimumWidth(column), Math.round(startWidth + nextX - clientX)),
        }));
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
    [widthFor]
  );

  return {
    leadColumn: LEAD_COLUMN,
    dataColumn: (id: string) => `data:${id}`,
    widthFor,
    startResize,
  };
}
