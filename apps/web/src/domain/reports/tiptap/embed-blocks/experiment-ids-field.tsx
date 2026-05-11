"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ReportEditorExperimentOption } from "../report-editor-context";

export interface ExperimentIdsFieldProps {
  experiments: ReportEditorExperimentOption[];
  value: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  label?: string;
}

/** Multi-select experiments — reused by metric, scalar, and artifact embed blocks. */
export function ExperimentIdsField({
  experiments,
  value,
  onChange,
  disabled,
  label = "Experiments in this block",
}: ExperimentIdsFieldProps) {
  const set = new Set(value);

  const toggle = (id: string, checked: boolean) => {
    const next = new Set(value);
    if (checked) {
      next.add(id);
    } else {
      next.delete(id);
    }
    onChange([...next]);
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium text-muted-foreground">{label}</Label>
      <ScrollArea className="h-36 rounded-md border border-border px-2 py-2">
        <div className="space-y-2 pr-2">
          {experiments.length === 0 ? (
            <p className="text-xs text-muted-foreground">No experiments in this project.</p>
          ) : (
            experiments.map((exp) => (
              <div key={exp.id} className="flex items-center gap-2">
                <Checkbox
                  id={`report-exp-${exp.id}`}
                  checked={set.has(exp.id)}
                  disabled={disabled}
                  onCheckedChange={(c) => toggle(exp.id, c === true)}
                />
                <label
                  htmlFor={`report-exp-${exp.id}`}
                  className="cursor-pointer truncate text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  {exp.name}
                </label>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
