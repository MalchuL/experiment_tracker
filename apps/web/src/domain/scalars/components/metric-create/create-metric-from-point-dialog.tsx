"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ScalarPointSelection } from "@/domain/scalars/types";

interface CreateMetricFromPointDialogProps {
  point: ScalarPointSelection | null;
  open: boolean;
  isSaving: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: {
    experimentId: string;
    name: string;
    value: number;
    label?: string | null;
  }) => void;
}

export function CreateMetricFromPointDialog({
  point,
  open,
  isSaving,
  onOpenChange,
  onSubmit,
}: CreateMetricFromPointDialogProps) {
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [label, setLabel] = useState("");

  useEffect(() => {
    if (!point || !open) return;
    setName(point.metricName);
    setValue(String(point.originalValue));
    setLabel("");
  }, [open, point]);

  const numericValue = Number(value);
  const canSubmit = !!point && name.trim().length > 0 && Number.isFinite(numericValue);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create metric from scalar point</DialogTitle>
        </DialogHeader>
        {point ? (
          <div className="space-y-3">
            <div className="rounded border bg-muted/30 p-2 text-xs">
              <div className="font-medium">{point.experimentName}</div>
              <div className="mt-1 break-all text-muted-foreground">{point.experimentId}</div>
              <div className="mt-1 text-muted-foreground">step {point.step}</div>
            </div>
            <Field label="Metric name">
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
            <Field label="Value">
              <Input value={value} onChange={(event) => setValue(event.target.value)} inputMode="decimal" />
            </Field>
            <Field label="Label">
              <Input
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder="Optional"
              />
            </Field>
          </div>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit || isSaving}
            onClick={() => {
              if (!point || !canSubmit) return;
              onSubmit({
                experimentId: point.experimentId,
                name: name.trim(),
                value: numericValue,
                label: label.trim() || null,
              });
            }}
          >
            {isSaving ? "Creating..." : "Create metric"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}
