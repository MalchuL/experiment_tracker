"use client";

import { Button } from "@/components/ui/button";
import type { ScalarPointSelection } from "@/domain/scalars/types";
import { formatScalarWireForDisplay } from "@/domain/scalars/utils/scalar-value";

interface ScalarPointContextMenuProps {
  point: ScalarPointSelection | null;
  position: { x: number; y: number } | null;
  onCreateMetric: (point: ScalarPointSelection) => void;
  onClose: () => void;
}

export function ScalarPointContextMenu({
  point,
  position,
  onCreateMetric,
  onClose,
}: ScalarPointContextMenuProps) {
  if (!point || !position) return null;

  return (
    <div className="fixed inset-0 z-50" onClick={onClose} onContextMenu={(event) => event.preventDefault()}>
      <div
        className="absolute min-w-56 rounded-md border bg-popover p-2 text-popover-foreground shadow-md"
        style={{ left: position.x, top: position.y }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-2 text-xs text-muted-foreground">
          <div className="truncate font-medium text-foreground">{point.metricName}</div>
          <div className="truncate">{point.experimentName}</div>
          <div>
            step {point.step}, value {formatScalarWireForDisplay(point.originalValue)}
          </div>
        </div>
        <Button size="sm" className="h-8 w-full text-xs" onClick={() => onCreateMetric(point)}>
          Create metric
        </Button>
      </div>
    </div>
  );
}
