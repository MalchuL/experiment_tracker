"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ExperimentDiffIcon,
  experimentDiffSurfaceClass,
  type ExperimentDiffStatus,
} from "@/components/shared/experiment-diff-ui";
import { ProjectDataTableFrame, useProjectDataTableFrame } from "@/components/shared/project-data-table-frame";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { CompareLabeledSwitch } from "./compare-labeled-switch";
import {
  loadCompareBoolean,
  saveCompareBoolean,
  useExperimentDataCompareLayout,
} from "../hooks/use-experiment-data-compare-layout";

export type ExperimentDataComparisonMode = "baseline" | "previous";
export type ExperimentDataOverflowMode = "wrap" | "truncate";
export type ExperimentDataDiffStatus = ExperimentDiffStatus | "missing";

export interface ExperimentDataCompareColumn {
  id: string;
  label: string;
  secondaryLabel?: string;
}

export interface ExperimentDataCompareRow<T> {
  id: string;
  label: string;
  depth?: number;
  values: (T | undefined)[];
}

export type ExperimentDataCompareRenderValue<T> = (
  value: T | undefined,
  referenceValue: T | undefined,
  status: ExperimentDataDiffStatus,
  row: ExperimentDataCompareRow<T>
) => ReactNode;

interface ExperimentDataCompareTableProps<T> {
  storageScope: string;
  leadColumnLabel: string;
  columns: ExperimentDataCompareColumn[];
  rows: ExperimentDataCompareRow<T>[];
  renderValue: ExperimentDataCompareRenderValue<T>;
  valueKey?: (value: T) => string;
  valueTitle?: ExperimentDataCompareRenderValue<T>;
  defaultPinLeadColumn?: boolean;
  defaultComparisonMode?: ExperimentDataComparisonMode;
  defaultOverflowMode?: ExperimentDataOverflowMode;
  defaultLeadOverflowMode?: ExperimentDataOverflowMode;
}

export function classifyExperimentDataRow<T>(
  values: (T | undefined)[],
  mode: ExperimentDataComparisonMode,
  valueKey: (value: T) => string
): ExperimentDataDiffStatus[] {
  return values.map((value, index) => {
    if (index === 0) return value === undefined ? "missing" : "unchanged";
    const reference = mode === "previous" ? values[index - 1] : values[0];
    if (reference === undefined) return value === undefined ? "missing" : "added";
    if (value === undefined) return "removed";
    return valueKey(reference) === valueKey(value) ? "unchanged" : "changed";
  });
}

export function referenceValueForCompareCell<T>(
  values: (T | undefined)[],
  index: number,
  mode: ExperimentDataComparisonMode
): T | undefined {
  if (index === 0) return undefined;
  return mode === "previous" ? values[index - 1] : values[0];
}

export function ExperimentDataCompareTable<T>({
  storageScope,
  leadColumnLabel,
  columns,
  rows,
  renderValue,
  valueKey = (value) => JSON.stringify(value),
  valueTitle = defaultValueTitle,
  defaultPinLeadColumn = true,
  defaultComparisonMode = "baseline",
  defaultOverflowMode = "wrap",
  defaultLeadOverflowMode = "truncate",
}: ExperimentDataCompareTableProps<T>) {
  const [pinLeadColumn, setPinLeadColumn] = useState(defaultPinLeadColumn);
  const [compareWithPrevious, setCompareWithPrevious] = useState(
    defaultComparisonMode === "previous"
  );
  const [wrapValues, setWrapValues] = useState(defaultOverflowMode === "wrap");
  const [wrapLeadColumn, setWrapLeadColumn] = useState(defaultLeadOverflowMode === "wrap");

  useEffect(() => {
    setPinLeadColumn(loadCompareBoolean(storageScope, "pin-lead", defaultPinLeadColumn));
    setCompareWithPrevious(
      loadCompareBoolean(storageScope, "compare-previous", defaultComparisonMode === "previous")
    );
    setWrapValues(loadCompareBoolean(storageScope, "wrap-values", defaultOverflowMode === "wrap"));
    setWrapLeadColumn(
      loadCompareBoolean(storageScope, "wrap-lead", defaultLeadOverflowMode === "wrap")
    );
  }, [
    defaultComparisonMode,
    defaultLeadOverflowMode,
    defaultOverflowMode,
    defaultPinLeadColumn,
    storageScope,
  ]);

  const mode: ExperimentDataComparisonMode = compareWithPrevious ? "previous" : "baseline";
  const rowsWithStatuses = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        statuses: classifyExperimentDataRow(row.values, mode, valueKey),
      })),
    [mode, rows, valueKey]
  );

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-end gap-4 border-b px-4 py-2">
        <CompareLabeledSwitch
          id={`${storageScope}-pin-lead`}
          label={`Pin ${leadColumnLabel.toLowerCase()} column`}
          checked={pinLeadColumn}
          onCheckedChange={(checked) => {
            setPinLeadColumn(checked);
            saveCompareBoolean(storageScope, "pin-lead", checked);
          }}
          tip={`Keep ${leadColumnLabel.toLowerCase()} names visible while scrolling horizontally.`}
        />
        <CompareLabeledSwitch
          id={`${storageScope}-compare-previous`}
          label="Compare with previous"
          checked={compareWithPrevious}
          onCheckedChange={(checked) => {
            setCompareWithPrevious(checked);
            saveCompareBoolean(storageScope, "compare-previous", checked);
          }}
          tip={
            compareWithPrevious
              ? "Each experiment is compared with the column immediately to its left."
              : "Each experiment is compared with the first selected experiment."
          }
        />
        <CompareLabeledSwitch
          id={`${storageScope}-wrap-lead`}
          label={`Wrap ${leadColumnLabel.toLowerCase()} names`}
          checked={wrapLeadColumn}
          onCheckedChange={(checked) => {
            setWrapLeadColumn(checked);
            saveCompareBoolean(storageScope, "wrap-lead", checked);
          }}
          tip={`Wrap long ${leadColumnLabel.toLowerCase()} names onto multiple lines.`}
        />
        <CompareLabeledSwitch
          id={`${storageScope}-wrap-values`}
          label="Wrap values"
          checked={wrapValues}
          onCheckedChange={(checked) => {
            setWrapValues(checked);
            saveCompareBoolean(storageScope, "wrap-values", checked);
          }}
          tip="Wrap long values onto multiple lines. Turn off to truncate them to one line."
        />
      </div>
      <ProjectDataTableFrame
        pinLeadColumns={pinLeadColumn}
        leadColumnCount={1}
        className="rounded-none border-0 bg-background"
      >
        <ExperimentDataCompareTableContent
          storageScope={storageScope}
          leadColumnLabel={leadColumnLabel}
          columns={columns}
          rows={rowsWithStatuses}
          renderValue={renderValue}
          valueTitle={valueTitle}
          leadOverflowMode={wrapLeadColumn ? "wrap" : "truncate"}
          overflowMode={wrapValues ? "wrap" : "truncate"}
          comparisonMode={mode}
        />
      </ProjectDataTableFrame>
    </div>
  );
}

function ExperimentDataCompareTableContent<T>({
  storageScope,
  leadColumnLabel,
  columns,
  rows,
  renderValue,
  valueTitle,
  leadOverflowMode,
  overflowMode,
  comparisonMode,
}: {
  storageScope: string;
  leadColumnLabel: string;
  columns: ExperimentDataCompareColumn[];
  rows: (ExperimentDataCompareRow<T> & { statuses: ExperimentDataDiffStatus[] })[];
  renderValue: ExperimentDataCompareRenderValue<T>;
  valueTitle: ExperimentDataCompareRenderValue<T>;
  leadOverflowMode: ExperimentDataOverflowMode;
  overflowMode: ExperimentDataOverflowMode;
  comparisonMode: ExperimentDataComparisonMode;
}) {
  const { pinLeadColumns, leadColumnCount } = useProjectDataTableFrame();
  const { leadColumn, dataColumn, widthFor, startResize } =
    useExperimentDataCompareLayout(storageScope);
  const pinLead = pinLeadColumns && leadColumnCount >= 1;
  const leadWidth = widthFor(leadColumn);
  const columnWidths = columns.map((column) => widthFor(dataColumn(column.id)));
  const totalWidth = leadWidth + columnWidths.reduce((sum, width) => sum + width, 0);

  return (
    <Table
      containerClassName="overflow-visible w-full min-w-0"
      className="table-fixed border-separate border-spacing-0"
      style={{ width: totalWidth }}
    >
      <TableHeader className="sticky top-0 z-20 bg-background shadow-[0_1px_0_0_hsl(var(--border))]">
        <TableRow className="hover:bg-transparent">
          <TableHead
            className={cn(
              "relative h-12 box-border overflow-hidden border-r bg-background px-4 text-xs",
              pinLead && "sticky left-0 z-[21]"
            )}
            style={fixedWidth(leadWidth)}
          >
            {leadColumnLabel}
            <HeaderResizeHandle
              label={leadColumnLabel}
              onBegin={(clientX) => startResize(leadColumn, clientX)}
            />
          </TableHead>
          {columns.map((column, index) => (
            <TableHead
              key={column.id}
              className="relative h-12 box-border overflow-hidden border-r bg-background px-4"
              style={fixedWidth(columnWidths[index] ?? 0)}
              title={column.label}
            >
              <div className="truncate text-xs font-medium text-foreground">{column.label}</div>
              {index === 0 ? (
                <div className="mt-0.5 text-[11px] font-normal text-muted-foreground">
                  {comparisonMode === "previous" ? "Start" : "Baseline"}
                </div>
              ) : null}
              {column.secondaryLabel ? (
                <div className="mt-0.5 truncate text-[11px] font-normal text-muted-foreground">
                  {column.secondaryLabel}
                </div>
              ) : null}
              <HeaderResizeHandle
                label={column.label}
                onBegin={(clientX) => startResize(dataColumn(column.id), clientX)}
              />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id} className="group hover:bg-transparent">
            <TableCell
              className={cn(
                "box-border border-r bg-background px-4 py-2.5 font-mono text-xs text-foreground/80 transition-colors group-hover:bg-muted/50",
                leadOverflowMode === "wrap"
                  ? "whitespace-normal break-words"
                  : "overflow-hidden whitespace-nowrap",
                pinLead && "sticky left-0 z-[2]"
              )}
              style={{
                ...fixedWidth(leadWidth),
                paddingLeft: `${16 + Math.max(0, row.depth ?? 0) * 10}px`,
              }}
              title={row.label}
            >
              <div className={leadOverflowMode === "truncate" ? "truncate" : undefined}>
                {row.label}
              </div>
            </TableCell>
            {row.values.map((value, index) => {
              const status = row.statuses[index] ?? "missing";
              const referenceValue = referenceValueForCompareCell(row.values, index, comparisonMode);
              return (
                <TableCell
                  key={columns[index]?.id ?? index}
                  className={cn(
                    "box-border border-r px-4 py-2.5 align-top transition-colors group-hover:bg-muted/50",
                    overflowMode === "wrap"
                      ? "whitespace-normal break-words"
                      : "overflow-hidden whitespace-nowrap",
                    experimentDiffSurfaceClass(status === "missing" ? "removed" : status)
                  )}
                  style={fixedWidth(columnWidths[index] ?? 0)}
                  title={String(valueTitle(value, referenceValue, status, row) ?? "")}
                >
                  <div className={overflowMode === "truncate" ? "truncate" : undefined}>
                    {renderValue(value, referenceValue, status, row)}
                  </div>
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function defaultValueTitle<T>(
  value: T | undefined,
  _referenceValue: T | undefined,
  _status: ExperimentDataDiffStatus,
  _row: ExperimentDataCompareRow<T>
): string {
  if (value === undefined) return "Not set";
  if (typeof value === "string") return value;
  const serialized = JSON.stringify(value);
  return serialized ?? String(value);
}

function fixedWidth(width: number) {
  return { width, minWidth: width, maxWidth: width };
}

function HeaderResizeHandle({
  label,
  onBegin,
}: {
  label: string;
  onBegin: (clientX: number) => void;
}) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={`Resize ${label} column`}
      onMouseDown={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onBegin(event.clientX);
      }}
      onTouchStart={(event) => {
        event.preventDefault();
        event.stopPropagation();
        const touch = event.touches[0];
        if (touch) onBegin(touch.clientX);
      }}
      className="absolute right-0 top-0 z-10 flex h-full w-2.5 cursor-col-resize touch-none select-none items-center justify-center"
    >
      <span className="block h-[calc(100%-1rem)] w-px bg-border transition-colors hover:bg-muted-foreground/70" />
    </div>
  );
}

export function ExperimentDataDiffValue({
  status,
  children,
}: {
  status: ExperimentDataDiffStatus;
  children: ReactNode;
}) {
  const visualStatus: ExperimentDiffStatus = status === "missing" ? "removed" : status;
  return (
    <div className="grid min-w-0 grid-cols-[1rem_minmax(0,1fr)] items-start gap-1.5">
      <span className="flex h-4 items-center justify-center">
        <ExperimentDiffIcon status={visualStatus} />
      </span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
