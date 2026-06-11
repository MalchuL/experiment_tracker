"use client";

import { useRef } from "react";
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

export type LoggedMetricAddDialogMode = "new-label" | "group";

export function LoggedMetricAddDialog({
  open,
  onOpenChange,
  mode,
  groupLabel,
  newName,
  onNewNameChange,
  newLabel,
  onNewLabelChange,
  newValue,
  onNewValueChange,
  onAdd,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: LoggedMetricAddDialogMode;
  groupLabel: string | null;
  newName: string;
  onNewNameChange: (value: string) => void;
  newLabel: string;
  onNewLabelChange: (value: string) => void;
  newValue: string;
  onNewValueChange: (value: string) => void;
  onAdd: () => void | Promise<void>;
}) {
  const nameInputRef = useRef<HTMLInputElement>(null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          nameInputRef.current?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle>Add metric</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          {mode === "new-label" ? (
            <div className="space-y-1">
              <Label htmlFor="logged-metric-new-label">Label (optional)</Label>
              <Input
                id="logged-metric-new-label"
                value={newLabel}
                onChange={(event) => onNewLabelChange(event.target.value)}
                placeholder="e.g. fold_1"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty to add an unlabeled metric.
              </p>
            </div>
          ) : (
            <div className="rounded-md bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
              {groupLabel != null ? (
                <>
                  Adding under label: <span className="font-medium text-foreground">{groupLabel}</span>
                </>
              ) : (
                "Adding unlabeled metric"
              )}
            </div>
          )}
          <div className="space-y-1">
            <Label htmlFor="logged-metric-new-name">Name</Label>
            <Input
              ref={nameInputRef}
              id="logged-metric-new-name"
              value={newName}
              onChange={(event) => onNewNameChange(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Value</Label>
            <Input value={newValue} onChange={(event) => onNewValueChange(event.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => void onAdd()}>Add</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
