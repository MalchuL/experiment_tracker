"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnOrderState,
  type SortingState,
} from "@tanstack/react-table";
import { useCurrentProject } from "@/domain/projects/hooks";
import { useProjectMetricLabels, useProjectMetricsByLabel } from "@/domain/metrics/hooks";
import { CHART_COLORS } from "@/domain/scalars/constants";
import { useSelectedExperimentStore } from "@/domain/experiments/store";
import type { MetricsTableRow } from "../lib/types";
import { loadPersistedMetricsUi, savePersistedMetricsUi } from "../lib/persisted-ui";
import { metricCellStyleKey } from "../lib/constants";
import { useMetricTableColumns } from "./use-metric-table-columns";

/**
 * All state for the project metrics pivot page: data loading, persisted table prefs, edit-session
 * (row/column/tints), and the TanStack Table instance.
 */
export function useProjectMetricsPageState() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const { data: labelData, isLoading: labelsLoading } = useProjectMetricLabels(projectId);
  const { selectedExperimentId, setSelectedExperimentId } = useSelectedExperimentStore();
  const onSelectExperiment = useCallback(
    (id: string) => {
      setSelectedExperimentId(id);
    },
    [setSelectedExperimentId]
  );
  const [label, setLabel] = useState<string | null>(null);
  const [includeAll, setIncludeAll] = useState(false);
  const [nameFilter, setNameFilter] = useState("");
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>([]);
  const [columnSizing, setColumnSizing] = useState<Record<string, number>>({});
  const [sorting, setSorting] = useState<SortingState>([]);

  const [editMode, setEditMode] = useState(false);
  const [hiddenRowIds, setHiddenRowIds] = useState<Set<string>>(() => new Set());
  const [hiddenColumnIds, setHiddenColumnIds] = useState<Set<string>>(
    () => new Set<string>(["experimentId", "createdAt"])
  );
  const [minHighlightColumnIds, setMinHighlightColumnIds] = useState<Set<string>>(() => new Set());
  const [maxHighlightColumnIds, setMaxHighlightColumnIds] = useState<Set<string>>(() => new Set());
  const [cellTints, setCellTints] = useState<Record<string, 1 | 2 | 3 | 4>>({});

  const cycleCellTint = useCallback((experimentId: string, metricName: string) => {
    setCellTints((prev) => {
        const k = metricCellStyleKey({ experimentId }, metricName);
        const cur = prev[k];
        let next: 0 | 1 | 2 | 3 | 4;
        if (cur === undefined) next = 1;
        else if (cur < 4) next = (cur + 1) as 1 | 2 | 3 | 4;
        else next = 0;
        if (next === 0) {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { [k]: _d, ...rest } = prev;
          return rest;
        }
        return { ...prev, [k]: next as 1 | 2 | 3 | 4 };
      });
  }, []);

  useEffect(() => {
    if (!projectId) return;
    const s = loadPersistedMetricsUi(projectId);
    if (s?.includeAll != null) setIncludeAll(!!s.includeAll);
    if (s?.columnSizing) setColumnSizing(s.columnSizing);
    if (s?.label !== undefined) setLabel(s.label);
  }, [projectId]);

  useEffect(() => {
    if (labelData == null || label !== null) return;
    if (labelData.labels.length > 0) {
      setLabel(labelData.labels[0]!);
    } else if (labelData.hasUnlabeled) {
      setLabel("");
    }
  }, [labelData, label]);

  const { data: pages, fetchNextPage, hasNextPage, isFetchingNextPage, isPending: dataLoading, isError } =
    useProjectMetricsByLabel(projectId, label, includeAll);

  const latest = pages?.pages?.[pages.pages.length - 1];
  const baseNames = latest?.metricNames ?? pages?.pages?.[0]?.metricNames ?? [];
  const flatRows: MetricsTableRow[] = useMemo(() => {
    const all = pages?.pages.flatMap((p) => p.rows) ?? [];
    const sorted = [...all].sort((a, b) => {
      const ta =
        a.createdAt != null && a.createdAt !== "" ? Date.parse(a.createdAt) : 0;
      const tb =
        b.createdAt != null && b.createdAt !== "" ? Date.parse(b.createdAt) : 0;
      if (Number.isFinite(tb) && Number.isFinite(ta) && tb !== ta) {
        return tb - ta;
      }
      return b.experimentId.localeCompare(a.experimentId);
    });
    return sorted.map((r, idx) => {
      const byName: Record<string, number | null> = {};
      baseNames.forEach((n, i) => {
        byName[n] = r.values[i] ?? null;
      });
      return {
        experimentId: r.experimentId,
        experimentName: r.experimentName,
        createdAt: r.createdAt ?? "",
        experimentColor: r.color ?? CHART_COLORS[idx % CHART_COLORS.length]!,
        byName,
      };
    });
  }, [pages, baseNames]);

  const metricNameKey = useMemo(() => baseNames.join("|"), [baseNames]);
  const metricKeySeen = useRef("");

  useEffect(() => {
    if (baseNames.length === 0) return;
    const keyChanged = metricKeySeen.current !== metricNameKey;
    metricKeySeen.current = metricNameKey;
    setColumnOrder((raw) => {
      const co = raw.map((c) =>
        c === "experiment_id" ? "experimentId" : c === "created_at" ? "createdAt" : c
      );
      const fixed = (c: string) => c === "experiment" || c === "experimentId" || c === "createdAt";
      const savedMetricOrder = projectId ? loadPersistedMetricsUi(projectId)?.columnOrder : undefined;
      const fromData = co.filter(
        (c) => !fixed(c) && baseNames.includes(c)
      );
      let middle: string[] = [];
      if (fromData.length > 0) {
        for (const c of fromData) {
          if (baseNames.includes(c) && !middle.includes(c)) middle.push(c);
        }
        for (const b of baseNames) {
          if (!middle.includes(b)) middle.push(b);
        }
      } else {
        const s = (savedMetricOrder ?? []).filter((c) => baseNames.includes(c));
        for (const c of s) {
          if (!middle.includes(c)) middle.push(c);
        }
        for (const b of baseNames) {
          if (!middle.includes(b)) middle.push(b);
        }
      }
      const next = ["experiment" as const, ...middle, "experimentId" as const, "createdAt" as const];
      if (!keyChanged && co.length > 0 && co.length === next.length && co.every((id, i) => id === next[i])) {
        return raw;
      }
      return next;
    });
  }, [baseNames, metricNameKey, projectId]);

  const filteredRows = useMemo(() => {
    const q = nameFilter.trim().toLowerCase();
    if (!q) return flatRows;
    return flatRows.filter((r) => r.experimentName.toLowerCase().includes(q));
  }, [flatRows, nameFilter]);

  const rowsInReport = useMemo(
    () => filteredRows.filter((r) => !hiddenRowIds.has(r.experimentId)),
    [filteredRows, hiddenRowIds]
  );
  const tableData = useMemo(
    () => (editMode ? filteredRows : rowsInReport),
    [editMode, filteredRows, rowsInReport]
  );
  const colMinMax = useMemo(() => {
    const out: Record<string, { min: number; max: number }> = {};
    for (const n of baseNames) {
      const nums = rowsInReport
        .map((r) => r.byName[n])
        .filter((v): v is number => v != null && Number.isFinite(v));
      if (nums.length === 0) continue;
      out[n] = { min: Math.min(...nums), max: Math.max(...nums) };
    }
    return out;
  }, [baseNames, rowsInReport]);

  const columnVisibility = useMemo(() => {
    const vis: Record<string, boolean> = { experiment: true };
    for (const n of baseNames) {
      vis[n] = editMode ? true : !hiddenColumnIds.has(n);
    }
    vis["experimentId"] = editMode ? true : !hiddenColumnIds.has("experimentId");
    vis["createdAt"] = editMode ? true : !hiddenColumnIds.has("createdAt");
    return vis;
  }, [baseNames, editMode, hiddenColumnIds]);

  const columns = useMetricTableColumns({
    baseNames,
    editMode,
    hiddenRowIds,
    setHiddenRowIds,
    hiddenColumnIds,
    setHiddenColumnIds,
    minHighlightColumnIds,
    setMinHighlightColumnIds,
    maxHighlightColumnIds,
    setMaxHighlightColumnIds,
    colMinMax,
    cellTints,
    cycleCellTint,
    onSelectExperiment,
  });

  const table = useReactTable<MetricsTableRow>({
    data: tableData,
    columns,
    state: { columnOrder, columnSizing, sorting, columnVisibility },
    onColumnOrderChange: setColumnOrder,
    onColumnSizingChange: setColumnSizing,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    columnResizeMode: "onChange",
    getRowId: (r) => r.experimentId,
  });

  useEffect(() => {
    if (!projectId) return;
    const t = window.setTimeout(() => {
      savePersistedMetricsUi(projectId, {
        label: label ?? undefined,
        includeAll,
        columnOrder: columnOrder.filter(
          (c) => c !== "experiment" && c !== "experimentId" && c !== "createdAt"
        ),
        columnSizing,
      });
    }, 200);
    return () => clearTimeout(t);
  }, [projectId, label, includeAll, columnOrder, columnSizing]);

  const hasAnyLabel = (labelData?.labels.length ?? 0) > 0 || (labelData?.hasUnlabeled ?? false);

  return {
    project,
    projectId,
    projectLoading,
    labelsLoading,
    labelData,
    hasAnyLabel,
    label,
    setLabel,
    includeAll,
    setIncludeAll,
    nameFilter,
    setNameFilter,
    editMode,
    setEditMode,
    isError,
    dataLoading,
    latest,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    filteredRows,
    rowsInReport,
    tableData,
    table,
    hiddenRowIds,
    hiddenColumnIds,
    selectedExperimentId,
    setSelectedExperimentId,
  };
}
