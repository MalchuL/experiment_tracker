"use client";

import { cn } from "@/lib/utils";

interface ExperimentSelectionOrderBadgeProps {
  experimentId: string;
  experimentName: string;
  orderNumber: number | null;
  onToggle: () => void;
  className?: string;
}

export function ExperimentSelectionOrderBadge({
  experimentId,
  experimentName,
  orderNumber,
  onToggle,
  className,
}: ExperimentSelectionOrderBadgeProps) {
  const selected = orderNumber != null;

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className={cn(
        "box-border flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border p-0 text-[9px] font-medium leading-none tabular-nums transition-colors",
        selected
          ? "border-primary bg-primary text-primary-foreground"
          : "border-muted-foreground/40 bg-background hover:border-primary/60 hover:bg-muted/50",
        className
      )}
      aria-label={
        selected
          ? `Deselect ${experimentName} (compare order ${orderNumber})`
          : `Select ${experimentName} for compare`
      }
      aria-pressed={selected}
      data-testid={`button-selection-badge-${experimentId}`}
    >
      {selected ? orderNumber : null}
    </button>
  );
}
