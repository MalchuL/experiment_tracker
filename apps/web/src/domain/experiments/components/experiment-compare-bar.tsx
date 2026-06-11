"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { buildCompareHref } from "@/domain/experiments/lib/build-compare-href";
import { buildScalarsHref } from "@/domain/experiments/lib/build-scalars-href";
import { cn } from "@/lib/utils";

interface ExperimentCompareBarProps {
  projectId: string;
  orderedIds: string[];
  className?: string;
}

export function ExperimentCompareBar({
  projectId,
  orderedIds,
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
        </>
      ) : (
        <>
          <Button type="button" disabled data-testid="button-compare-selected-experiments">
            Compare
          </Button>
          <Button type="button" variant="outline" disabled data-testid="button-scalars-selected-experiments">
            Scalars
          </Button>
        </>
      )}
    </div>
  );
}
