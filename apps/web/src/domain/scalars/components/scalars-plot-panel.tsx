"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  ScalarsMetricsGrid,
  type ScalarsMetricsGridProps,
} from "./scalars-metrics-grid";
import { ScalarsPagination } from "./scalars-pagination";
import { CollapsiblePrefixGroup } from "./collapsible-prefix-group";
import { scalarPage as clampPage } from "../utils/scalar-pagination";
import { partitionNamesByPrefixForTab } from "../utils/scalars-content-layout";

export interface ScalarsPlotPanelProps {
  scalars: ScalarsMetricsGridProps;
  pagination: {
    scalarPage: number;
    scalarPageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
  };
}

export function ScalarsPlotPanel({
  scalars,
  pagination,
}: ScalarsPlotPanelProps) {
  const { visibleMetrics, chartDataByMetric } = scalars.metrics;
  const { scalarPage, scalarPageSize, onPageChange, onPageSizeChange } =
    pagination;
  const rootRef = useRef<HTMLDivElement>(null);
  const page = clampPage(scalarPage, visibleMetrics.length, scalarPageSize);
  useEffect(() => {
    if (page !== scalarPage) onPageChange(page);
  }, [page, scalarPage, onPageChange]);
  useEffect(() => {
    const scrollRoot = rootRef.current?.closest<HTMLElement>(
      "[data-scalar-scroll-root]",
    );
    if (scrollRoot) scrollRoot.scrollTop = 0;
  }, [page, scalarPageSize]);
  const partition = useMemo(
    () =>
      partitionNamesByPrefixForTab(
        visibleMetrics
          .slice((page - 1) * scalarPageSize, page * scalarPageSize)
          .map((metric) => metric.name),
      ),
    [visibleMetrics, page, scalarPageSize],
  );
  const grid = (names: string[]) => (
    <ScalarsMetricsGrid
      {...scalars}
      metrics={{
        chartDataByMetric,
        visibleMetrics: names.map((name) => ({ name })),
      }}
    />
  );
  return (
    <div ref={rootRef} className="space-y-4">
      <ScalarsPagination
        page={page}
        pageSize={scalarPageSize}
        total={visibleMetrics.length}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
      {partition.ungrouped.length > 0 && grid(partition.ungrouped)}
      {partition.groups.map((group) => (
        <CollapsiblePrefixGroup
          key={group.key}
          title={group.key}
          count={group.items.length}
        >
          {grid(group.items)}
        </CollapsiblePrefixGroup>
      ))}
    </div>
  );
}
