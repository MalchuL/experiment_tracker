"use client";

import { useEffect, useState } from "react";
import { Package } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReportEditorContext } from "../report-editor-context";
import { ExperimentIdsField } from "./experiment-ids-field";
import { ReportBlockChrome } from "./report-block-chrome";
import type { ArtifactEmbedAttrs } from "./types";

export interface ArtifactEmbedBlockProps {
  attrs: ArtifactEmbedAttrs;
  onAttrsChange: (patch: Partial<ArtifactEmbedAttrs>) => void;
  selected?: boolean;
  editable?: boolean;
}

/** Artifacts embed — filters experiments and optional name / step for logged artifacts. */
export function ArtifactEmbedBlock({
  attrs,
  onAttrsChange,
  selected,
  editable = true,
}: ArtifactEmbedBlockProps) {
  const { experiments } = useReportEditorContext();
  const [stepText, setStepText] = useState(
    () => (attrs.step === null || attrs.step === undefined ? "" : String(attrs.step)),
  );

  useEffect(() => {
    setStepText(attrs.step === null || attrs.step === undefined ? "" : String(attrs.step));
  }, [attrs.step]);

  const onStepBlur = () => {
    const trimmed = stepText.trim();
    if (!trimmed) {
      onAttrsChange({ step: null });
      return;
    }
    const n = Number(trimmed);
    onAttrsChange({ step: Number.isFinite(n) ? n : null });
  };

  return (
    <ReportBlockChrome
      icon={Package}
      title="Artifacts"
      description="Scope logged artifacts by experiment, optional name, and optional step."
      selected={selected}
    >
      <ExperimentIdsField
        experiments={experiments}
        value={attrs.experimentIds}
        onChange={(experimentIds) => onAttrsChange({ experimentIds })}
        disabled={!editable}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground">Name contains</Label>
          <Input
            value={attrs.nameFilter}
            disabled={!editable}
            onChange={(e) => onAttrsChange({ nameFilter: e.target.value })}
            placeholder="e.g. checkpoint"
            className="h-8 text-sm"
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground">Step (optional)</Label>
          <Input
            value={stepText}
            disabled={!editable}
            onChange={(e) => setStepText(e.target.value)}
            onBlur={onStepBlur}
            inputMode="numeric"
            placeholder="Any step"
            className="h-8 text-sm"
          />
        </div>
      </div>
    </ReportBlockChrome>
  );
}
