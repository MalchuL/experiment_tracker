"use client";

import { useMemo, type Dispatch, type SetStateAction } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import type { ColumnWidthPolicy } from "@/lib/table/column-width-policy";
import {
  experimentsTableColumnPolicy,
  metricColumnId,
} from "@/domain/experiments/lib/experiments-table-column-widths";
import type { MetricsTableRow } from "../lib/types";
import { SHOW_IN_REPORT_COLUMN_ID, SHOW_IN_REPORT_COLUMN_PX } from "../lib/constants";
import {
  CreatedAtCell,
  ExperimentColumnHeader,
  ExperimentIdCell,
  ExperimentNameCell,
  MetricColumnHeader,
  MetricValueCell,
  ReadonlyMetaColumnHeader,
  ShowInReportCell,
} from "../components/metric-table-column-parts";

const UNRESTRICTED_RESIZE_MIN_PX = 1;
const UNRESTRICTED_RESIZE_MAX_PX = Number.MAX_SAFE_INTEGER;

export type UseMetricTableColumnsOptions = {
  baseNames: string[];
  inferredMetricColumnWidths: Record<string, number>;
  editMode: boolean;
  hiddenRowIds: Set<string>;
  setHiddenRowIds: Dispatch<SetStateAction<Set<string>>>;
  hiddenColumnIds: Set<string>;
  setHiddenColumnIds: Dispatch<SetStateAction<Set<string>>>;
  minHighlightColumnIds: Set<string>;
  setMinHighlightColumnIds: Dispatch<SetStateAction<Set<string>>>;
  maxHighlightColumnIds: Set<string>;
  setMaxHighlightColumnIds: Dispatch<SetStateAction<Set<string>>>;
  colMinMax: Record<string, { min: number; max: number }>;
  cellTints: Record<string, 1 | 2 | 3 | 4>;
  cycleCellTint: (experimentId: string, metricName: string) => void;
  onSelectExperiment: (experimentId: string) => void;
  wrapExperimentNames: boolean;
  wrapValues: boolean;
};

function policyForPivotColumn(id: string): ColumnWidthPolicy {
  if (id === SHOW_IN_REPORT_COLUMN_ID) {
    return { mode: "fixed", defaultPx: SHOW_IN_REPORT_COLUMN_PX, minPx: SHOW_IN_REPORT_COLUMN_PX, maxPx: SHOW_IN_REPORT_COLUMN_PX };
  }
  if (id === "experiment") return experimentsTableColumnPolicy("experiment");
  if (id === "experimentId") {
    return { mode: "fixed", defaultPx: 140, minPx: 100, maxPx: 360 };
  }
  if (id === "createdAt") {
    return { mode: "fixed", defaultPx: 180, minPx: 140, maxPx: 300 };
  }
  return experimentsTableColumnPolicy(
    metricColumnId({ name: id, label: null, direction: "maximize", aggregation: "last" })
  );
}

/** Column defs for the pivot table (experiment + dynamic metric columns). */
export function useMetricTableColumns(o: UseMetricTableColumnsOptions) {
  const {
    baseNames,
    inferredMetricColumnWidths,
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
    wrapExperimentNames,
    wrapValues,
  } = o;

  return useMemo((): ColumnDef<MetricsTableRow, unknown>[] => {
    return [
      {
        id: SHOW_IN_REPORT_COLUMN_ID,
        header: () => null,
        accessorFn: (r) => !hiddenRowIds.has(r.experimentId),
        cell: (c) => (
          <ShowInReportCell
            row={c.row.original}
            hiddenRowIds={hiddenRowIds}
            setHiddenRowIds={setHiddenRowIds}
          />
        ),
        size: SHOW_IN_REPORT_COLUMN_PX,
        minSize: SHOW_IN_REPORT_COLUMN_PX,
        maxSize: SHOW_IN_REPORT_COLUMN_PX,
        enableSorting: false,
        enableResizing: false,
        meta: { widthPolicy: policyForPivotColumn(SHOW_IN_REPORT_COLUMN_ID) },
      } as ColumnDef<MetricsTableRow, unknown>,
      {
        id: "experiment",
        header: (ctx) => <ExperimentColumnHeader header={ctx} />,
        accessorFn: (r) => r.experimentName,
        cell: (c) => (
          <ExperimentNameCell
            row={c.row.original}
            onSelectExperiment={onSelectExperiment}
            wrapExperimentNames={wrapExperimentNames}
          />
        ),
        size: 200,
        minSize: UNRESTRICTED_RESIZE_MIN_PX,
        maxSize: UNRESTRICTED_RESIZE_MAX_PX,
        enableSorting: true,
        meta: { widthPolicy: policyForPivotColumn("experiment") },
      } as ColumnDef<MetricsTableRow, unknown>,
      ...baseNames.map(
        (n) =>
          ({
            id: n,
            header: (ctx) => (
              <MetricColumnHeader
                name={n}
                editMode={editMode}
                header={ctx}
                hiddenColumnIds={hiddenColumnIds}
                setHiddenColumnIds={setHiddenColumnIds}
                minHighlightColumnIds={minHighlightColumnIds}
                setMinHighlightColumnIds={setMinHighlightColumnIds}
                maxHighlightColumnIds={maxHighlightColumnIds}
                setMaxHighlightColumnIds={setMaxHighlightColumnIds}
              />
            ),
            accessorFn: (row) => row.byName[n] ?? undefined,
            cell: (c) => (
              <MetricValueCell
                row={c.row.original}
                metricName={n}
                value={c.getValue() as number | null}
                colMinMax={colMinMax}
                minHighlightColumnIds={minHighlightColumnIds}
                maxHighlightColumnIds={maxHighlightColumnIds}
                cellTints={cellTints}
                cycleCellTint={cycleCellTint}
                wrapValues={wrapValues}
              />
            ),
            size: inferredMetricColumnWidths[n] ?? 120,
            minSize: UNRESTRICTED_RESIZE_MIN_PX,
            maxSize: UNRESTRICTED_RESIZE_MAX_PX,
            enableSorting: true,
            sortUndefined: "last",
            meta: { widthPolicy: policyForPivotColumn(n) },
          }) as ColumnDef<MetricsTableRow, unknown>
      ),
      {
        id: "experimentId",
        header: () => (
          <ReadonlyMetaColumnHeader
            columnId="experimentId"
            editMode={editMode}
            hiddenColumnIds={hiddenColumnIds}
            setHiddenColumnIds={setHiddenColumnIds}
          />
        ),
        accessorKey: "experimentId",
        cell: (c) => <ExperimentIdCell value={c.getValue() as string} wrapValues={wrapValues} />,
        size: 140,
        minSize: UNRESTRICTED_RESIZE_MIN_PX,
        maxSize: UNRESTRICTED_RESIZE_MAX_PX,
        enableSorting: false,
        meta: { widthPolicy: policyForPivotColumn("experimentId") },
      } as ColumnDef<MetricsTableRow, unknown>,
      {
        id: "createdAt",
        header: () => (
          <ReadonlyMetaColumnHeader
            columnId="createdAt"
            editMode={editMode}
            hiddenColumnIds={hiddenColumnIds}
            setHiddenColumnIds={setHiddenColumnIds}
          />
        ),
        accessorFn: (r) => r.createdAt,
        cell: (c) => <CreatedAtCell raw={c.row.original.createdAt} wrapValues={wrapValues} />,
        size: 180,
        minSize: UNRESTRICTED_RESIZE_MIN_PX,
        maxSize: UNRESTRICTED_RESIZE_MAX_PX,
        enableSorting: false,
        meta: { widthPolicy: policyForPivotColumn("createdAt") },
      } as ColumnDef<MetricsTableRow, unknown>,
    ];
  }, [
    baseNames,
    inferredMetricColumnWidths,
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
    wrapExperimentNames,
    wrapValues,
  ]);
}
