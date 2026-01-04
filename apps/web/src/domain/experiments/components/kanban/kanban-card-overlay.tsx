"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Experiment } from "@/domain/experiments/types";

interface KanbanCardOverlayProps {
  experiment: Experiment;
}

export function KanbanCardOverlay({ experiment }: KanbanCardOverlayProps) {
  return (
    <Card className="shadow-lg rotate-2 w-64">
      <CardContent className="p-3">
        <div className="flex items-start gap-2">
          <div
            className="w-2 h-full rounded-full mt-1 flex-shrink-0"
            style={{ backgroundColor: experiment.color }}
          />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{experiment.name}</p>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              {experiment.id.slice(0, 8)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

