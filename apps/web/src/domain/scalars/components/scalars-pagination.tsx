"use client";

import { Button } from "@/components/ui/button";
import { scalarPage, SCALAR_PAGE_SIZES } from "../utils/scalar-pagination";

export interface ScalarsPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

export function ScalarsPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: ScalarsPaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav
      aria-label="Scalar pages"
      className="sticky top-0 z-20 flex flex-wrap items-center gap-2 bg-background py-2"
    >
      <Button
        size="sm"
        variant="outline"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <label className="text-sm">
        Page{" "}
        <input
          aria-label="Scalar page"
          type="number"
          min={1}
          max={pageCount}
          value={page}
          className="w-16 rounded border px-2 py-1"
          onChange={(event) =>
            onPageChange(
              scalarPage(Number(event.target.value), total, pageSize),
            )
          }
        />{" "}
        of {pageCount}
      </label>
      <Button
        size="sm"
        variant="outline"
        disabled={page === pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
      <label className="text-sm">
        Plots per page{" "}
        <select
          aria-label="Plots per page"
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
          className="rounded border bg-background px-2 py-1"
        >
          {SCALAR_PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
      <span className="text-sm text-muted-foreground">
        {total ? (page - 1) * pageSize + 1 : 0}–
        {Math.min(page * pageSize, total)} of {total} plots
      </span>
    </nav>
  );
}
