"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Experiment } from "@/domain/experiments/types";
import { ExperimentTruncatedText } from "@/domain/experiments/components/experiment-truncated-text";

interface KanbanCardOverlayProps {
  experiment: Experiment;
}

export function KanbanCardOverlay({ experiment }: KanbanCardOverlayProps) {
  return (
    <Card className="shadow-lg rotate-2 w-64">
      <CardContent className="p-3">
        <div className="flex items-center gap-2">
          <div
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: experiment.color }}
          />
          <div className="min-w-0 flex-1">
            <ExperimentTruncatedText text={experiment.name} className="text-sm font-medium" />
            {experiment.description ? (
              <ExperimentTruncatedText
                text={experiment.description}
                className="mt-0.5 text-xs text-muted-foreground"
              />
            ) : null}
            <p className="mt-0.5 font-mono text-xs text-muted-foreground">{experiment.id.slice(0, 8)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

