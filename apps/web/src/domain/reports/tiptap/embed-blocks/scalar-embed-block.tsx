"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReportEditorContext } from "../report-editor-context";
import { ExperimentIdsField } from "./experiment-ids-field";
import { ReportBlockChrome } from "./report-block-chrome";
import type { ScalarEmbedAttrs } from "./types";

export interface ScalarEmbedBlockProps {
  attrs: ScalarEmbedAttrs;
  onAttrsChange: (patch: Partial<ScalarEmbedAttrs>) => void;
  selected?: boolean;
  editable?: boolean;
}

/** Scalar series embed — documents which experiments and scalar keys to chart elsewhere. */
export function ScalarEmbedBlock({
  attrs,
  onAttrsChange,
  selected,
  editable = true,
}: ScalarEmbedBlockProps) {
  const { experiments } = useReportEditorContext();
  const [keysText, setKeysText] = useState(() => attrs.scalarKeys.join(", "));

  useEffect(() => {
    setKeysText(attrs.scalarKeys.join(", "));
  }, [attrs.scalarKeys]);

  const applyKeys = () => {
    const scalarKeys = keysText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    onAttrsChange({ scalarKeys });
  };

  return (
    <ReportBlockChrome
      icon={Activity}
      title="Scalars"
      description="Select experiments and scalar series keys. Open the Scalars page for full charts."
      selected={selected}
    >
      <ExperimentIdsField
        experiments={experiments}
        value={attrs.experimentIds}
        onChange={(experimentIds) => onAttrsChange({ experimentIds })}
        disabled={!editable}
      />
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground">
          Scalar keys (comma-separated)
        </Label>
        <Input
          value={keysText}
          disabled={!editable}
          onChange={(e) => setKeysText(e.target.value)}
          onBlur={applyKeys}
          placeholder="e.g. train/loss, eval/accuracy"
          className="h-8 text-sm"
        />
      </div>
    </ReportBlockChrome>
  );
}
