"use client";

import { useMemo, type Dispatch, type SetStateAction } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import type { MetricsTableRow } from "../lib/types";
import {
  CreatedAtCell,
  ExperimentColumnHeader,
  ExperimentIdCell,
  ExperimentNameCell,
  MetricColumnHeader,
  MetricValueCell,
  ReadonlyMetaColumnHeader,
} from "../components/metric-table-column-parts";

export type UseMetricTableColumnsOptions = {
  baseNames: string[];
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
};

/** Column defs for the pivot table (experiment + dynamic metric columns). */
export function useMetricTableColumns(o: UseMetricTableColumnsOptions) {
  const {
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
  } = o;

  return useMemo((): ColumnDef<MetricsTableRow, unknown>[] => {
    return [
      {
        id: "experiment",
        header: (ctx) => <ExperimentColumnHeader editMode={editMode} header={ctx} />,
        accessorFn: (r) => r.experimentName,
        cell: (c) => (
          <ExperimentNameCell
            row={c.row.original}
            editMode={editMode}
            hiddenRowIds={hiddenRowIds}
            setHiddenRowIds={setHiddenRowIds}
            onSelectExperiment={onSelectExperiment}
          />
        ),
        size: 200,
        minSize: 120,
        maxSize: 500,
        enableSorting: true,
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
            accessorFn: (row) => row.byName[n] ?? null,
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
              />
            ),
            size: 120,
            minSize: 72,
            maxSize: 400,
            enableSorting: true,
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
        cell: (c) => <ExperimentIdCell value={c.getValue() as string} />,
        size: 140,
        minSize: 100,
        maxSize: 360,
        enableSorting: false,
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
        cell: (c) => <CreatedAtCell raw={c.row.original.createdAt} />,
        size: 180,
        minSize: 140,
        maxSize: 300,
        enableSorting: false,
      } as ColumnDef<MetricsTableRow, unknown>,
    ];
  }, [
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
  ]);
}
