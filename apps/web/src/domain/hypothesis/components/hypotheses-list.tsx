"use client";

import { HypothesisCard } from "./hypothesis-card";
import type { Hypothesis } from "@/domain/hypothesis/types";
import type { Project } from "@/domain/projects/types";

interface HypothesesListProps {
  hypotheses: Hypothesis[];
  projectId: string;
  projects?: Project[];
  onDelete: (hypothesisId: string) => void;
}

export function HypothesesList({
  hypotheses,
  projectId,
  projects,
  onDelete,
}: HypothesesListProps) {
  return (
    <div className="space-y-3">
      {hypotheses.map((hypothesis) => {
        const project = projects?.find((p) => p.id === hypothesis.projectId);
        return (
          <HypothesisCard
            key={hypothesis.id}
            hypothesis={hypothesis}
            projectId={projectId}
            projectName={project?.name}
            onDelete={onDelete}
          />
        );
      })}
    </div>
  );
}

