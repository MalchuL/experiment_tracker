"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { buildCompareHref } from "@/domain/experiments/lib/build-compare-href";
import { buildScalarsHref } from "@/domain/experiments/lib/build-scalars-href";
import { cn } from "@/lib/utils";

interface ExperimentCompareBarProps {
  projectId: string;
  orderedIds: string[];
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  selectAllDisabled?: boolean;
  className?: string;
}

export function ExperimentCompareBar({
  projectId,
  orderedIds,
  onSelectAll,
  onClearSelection,
  selectAllDisabled = false,
  className,
}: ExperimentCompareBarProps) {
  const selectedCount = orderedIds.length;
  const compareHref = buildCompareHref(projectId, orderedIds);
  const scalarsHref = buildScalarsHref(projectId, orderedIds);

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-md border bg-card/95 px-3 py-2 shadow-md backdrop-blur-sm",
        className
      )}
      data-testid="experiment-compare-bar"
    >
      {selectedCount > 0 ? (
        <span className="text-sm text-muted-foreground">
          {selectedCount} selected
        </span>
      ) : null}
      {selectedCount > 0 ? (
        <>
          <Button asChild data-testid="button-compare-selected-experiments">
            <Link href={compareHref} target="_blank" rel="noopener noreferrer">
              Compare
            </Link>
          </Button>
          <Button asChild variant="outline" data-testid="button-scalars-selected-experiments">
            <Link href={scalarsHref} target="_blank" rel="noopener noreferrer">
              Scalars
            </Link>
          </Button>
          {onSelectAll || onClearSelection ? (
            <div className="h-6 w-px shrink-0 bg-border" aria-hidden="true" />
          ) : null}
          {onSelectAll ? (
            <Button
              type="button"
              variant="secondary"
              onClick={onSelectAll}
              disabled={selectAllDisabled}
              data-testid="button-select-all-experiments"
            >
              Select All
            </Button>
          ) : null}
          {onClearSelection ? (
            <Button
              type="button"
              variant="secondary"
              onClick={onClearSelection}
              disabled={selectedCount === 0}
              data-testid="button-clear-selected-experiments"
            >
              Clear
            </Button>
          ) : null}
        </>
      ) : (
        <>
          <Button type="button" disabled data-testid="button-compare-selected-experiments">
            Compare
          </Button>
          <Button type="button" variant="outline" disabled data-testid="button-scalars-selected-experiments">
            Scalars
          </Button>
          {onSelectAll || onClearSelection ? (
            <div className="h-6 w-px shrink-0 bg-border" aria-hidden="true" />
          ) : null}
          {onSelectAll ? (
            <Button
              type="button"
              variant="secondary"
              onClick={onSelectAll}
              disabled={selectAllDisabled}
              data-testid="button-select-all-experiments"
            >
              Select All
            </Button>
          ) : null}
          {onClearSelection ? (
            <Button
              type="button"
              variant="secondary"
              onClick={onClearSelection}
              disabled
              data-testid="button-clear-selected-experiments"
            >
              Clear
            </Button>
          ) : null}
        </>
      )}
    </div>
  );
}
